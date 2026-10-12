// Signal-processing helpers for the on-device engine.
// Each function mirrors the Python reference (validation/lite_digitizer.py,
// validation/ecg_measure.py, which use numpy/scipy) so results can be compared.
import 'dart:math' as math;
import 'dart:typed_data';

/// Second-order-section-free IIR (direct form II transposed), like scipy.signal.lfilter.
Float64List lfilter(List<double> b, List<double> a, List<double> x, List<double> zi) {
  final n = b.length;
  final z = List<double>.of(zi);
  final y = Float64List(x.length);
  for (var i = 0; i < x.length; i++) {
    final xi = x[i];
    final yi = b[0] * xi + z[0];
    for (var k = 1; k < n; k++) {
      z[k - 1] = (k < n - 1 ? z[k] : 0.0) + b[k] * xi - a[k] * yi;
    }
    y[i] = yi;
  }
  return y;
}

/// scipy.signal.filtfilt with default padtype='odd', padlen = 3 * max(len(a), len(b)).
Float64List filtfilt(List<double> b, List<double> a, List<double> zi, List<double> x) {
  final int padlen = 3 * math.max(a.length, b.length);
  if (x.length <= padlen) return Float64List.fromList(x);
  final ext = Float64List(x.length + 2 * padlen);
  for (var i = 0; i < padlen; i++) {
    ext[i] = 2 * x[0] - x[padlen - i];
  }
  for (var i = 0; i < x.length; i++) {
    ext[padlen + i] = x[i];
  }
  for (var i = 0; i < padlen; i++) {
    ext[padlen + x.length + i] = 2 * x[x.length - 1] - x[x.length - 2 - i];
  }
  var y = lfilter(b, a, ext, [for (final z in zi) z * ext[0]]);
  final rev = Float64List.fromList(y.reversed.toList());
  y = lfilter(b, a, rev, [for (final z in zi) z * rev[0]]);
  final out = Float64List(x.length);
  for (var i = 0; i < x.length; i++) {
    out[i] = y[y.length - 1 - (padlen + i)];
  }
  return out;
}

/// Butterworth band-pass filters used by the measurements (order 2, fs = 100 Hz),
/// coefficients from scipy.signal.butter / lfilter_zi.
class Band {
  const Band(this.b, this.a, this.zi);
  final List<double> b, a, zi;
  Float64List apply(List<double> x) => filtfilt(b, a, zi, x);

  static const qrs = Band(
    [0.29289321881345237, 0.0, -0.5857864376269047, 0.0, 0.29289321881345237],
    [1.0, -1.2840790438404124, 0.48293961719373135, -0.22031313360486263, 0.17157287525380982],
    [-0.29289321881345154, -0.2928932188134526, 0.2928932188134525, 0.2928932188134523],
  ); // 5-30 Hz
  static const pWave = Band(
    [0.10407835675609702, 0.0, -0.20815671351219403, 0.0, 0.10407835675609702],
    [1.0, -2.7230533328330813, 2.8589374789384174, -1.4470372030495535, 0.3197324698827336],
    [-0.10407835675609026, -0.10407835675610867, 0.10407835675610469, 0.10407835675609486],
  ); // 2-15 Hz
}

/// scipy.signal.find_peaks with the options this engine uses (height, distance, prominence).
/// Order of filtering matches scipy: height, distance (highest first), prominence.
List<int> findPeaks(List<double> x, {double? height, int? distance, double? prominence}) {
  // 1. local maxima, plateaus resolved to their middle (scipy _local_maxima_1d)
  final peaks = <int>[];
  var i = 1;
  final iMax = x.length - 1;
  while (i < iMax) {
    if (x[i - 1] < x[i]) {
      var ahead = i + 1;
      while (ahead < iMax && x[ahead] == x[i]) {
        ahead++;
      }
      if (x[ahead] < x[i]) {
        peaks.add((i + ahead - 1) ~/ 2);
        i = ahead;
      }
    }
    i++;
  }
  var p = peaks;
  if (height != null) p = [for (final k in p) if (x[k] >= height) k];
  if (distance != null && distance > 1 && p.length > 1) {
    final keep = List<bool>.filled(p.length, true);
    final order = List<int>.generate(p.length, (j) => j)..sort((a, b) => x[p[a]].compareTo(x[p[b]]));
    for (var oi = order.length - 1; oi >= 0; oi--) {
      final j = order[oi];
      if (!keep[j]) continue;
      var k = j - 1;
      while (k >= 0 && p[j] - p[k] < distance) {
        keep[k] = false;
        k--;
      }
      k = j + 1;
      while (k < p.length && p[k] - p[j] < distance) {
        keep[k] = false;
        k++;
      }
    }
    p = [for (var j = 0; j < p.length; j++) if (keep[j]) p[j]];
  }
  if (prominence != null) {
    p = [for (final k in p) if (peakProminence(x, k) >= prominence) k];
  }
  return p;
}

/// Prominence of one peak (scipy, wlen = None).
double peakProminence(List<double> x, int peak) {
  var leftMin = x[peak];
  var i = peak;
  while (i >= 0 && x[i] <= x[peak]) {
    if (x[i] < leftMin) leftMin = x[i];
    i--;
  }
  var rightMin = x[peak];
  i = peak;
  while (i < x.length && x[i] <= x[peak]) {
    if (x[i] < rightMin) rightMin = x[i];
    i++;
  }
  return x[peak] - math.max(leftMin, rightMin);
}

/// Least-squares polynomial of degree 2: returns [c2, c1, c0] (np.polyfit order).
List<double> polyfit2(List<double> xs, List<double> ys) {
  // normal equations on centred x for numerical stability
  final n = xs.length;
  final mx = xs.reduce((a, b) => a + b) / n;
  double s0 = n.toDouble(), s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0;
  for (var i = 0; i < n; i++) {
    final u = xs[i] - mx, y = ys[i];
    final u2 = u * u;
    s1 += u;
    s2 += u2;
    s3 += u2 * u;
    s4 += u2 * u2;
    t0 += y;
    t1 += u * y;
    t2 += u2 * y;
  }
  final m = [
    [s4, s3, s2, t2],
    [s3, s2, s1, t1],
    [s2, s1, s0, t0],
  ];
  for (var c = 0; c < 3; c++) {
    var piv = c;
    for (var r = c + 1; r < 3; r++) {
      if (m[r][c].abs() > m[piv][c].abs()) piv = r;
    }
    final tmp = m[c];
    m[c] = m[piv];
    m[piv] = tmp;
    for (var r = 0; r < 3; r++) {
      if (r == c || m[c][c] == 0) continue;
      final f = m[r][c] / m[c][c];
      for (var k = c; k < 4; k++) {
        m[r][k] -= f * m[c][k];
      }
    }
  }
  final a = m[0][3] / m[0][0], b = m[1][3] / m[1][1], cc = m[2][3] / m[2][2];
  // expand a*(x-mx)^2 + b*(x-mx) + c into powers of x
  return [a, b - 2 * a * mx, a * mx * mx - b * mx + cc];
}

double polyval(List<double> c, double x) => (c[0] * x + c[1]) * x + c[2];
double polyderAt(List<double> c, double x) => 2 * c[0] * x + c[1];

/// np.interp with NaN outside [xp.first, xp.last] (left=right=NaN). xp must be increasing.
Float64List interpNan(List<double> x, List<double> xp, List<double> fp) {
  final out = Float64List(x.length);
  var j = 0;
  for (var i = 0; i < x.length; i++) {
    final xi = x[i];
    if (xp.isEmpty || xi < xp.first || xi > xp.last) {
      out[i] = double.nan;
      continue;
    }
    while (j < xp.length - 2 && xp[j + 1] < xi) {
      j++;
    }
    while (j > 0 && xp[j] > xi) {
      j--;
    }
    final x0 = xp[j], x1 = xp[j + 1];
    final t = x1 == x0 ? 0.0 : (xi - x0) / (x1 - x0);
    out[i] = fp[j] + t * (fp[j + 1] - fp[j]);
  }
  return out;
}

double median(Iterable<double> v) {
  final s = v.where((e) => !e.isNaN).toList()..sort();
  if (s.isEmpty) return double.nan;
  final m = s.length ~/ 2;
  return s.length.isOdd ? s[m] : (s[m - 1] + s[m]) / 2;
}

double mean(List<double> v) => v.isEmpty ? double.nan : v.reduce((a, b) => a + b) / v.length;

double std(List<double> v) {
  if (v.isEmpty) return double.nan;
  final m = mean(v);
  return math.sqrt(v.map((e) => (e - m) * (e - m)).reduce((a, b) => a + b) / v.length);
}

double variance(List<double> v) {
  final s = std(v);
  return s * s;
}

/// Gaussian smoothing with edge padding, radius 3 sigma (as lite_digitizer.gaussian_smooth).
Float64List gaussianSmooth(List<double> x, double sigma) {
  final r = math.max(1, (3 * sigma).toInt());
  final k = List<double>.generate(2 * r + 1, (i) => math.exp(-0.5 * math.pow((i - r) / sigma, 2)));
  final ks = k.reduce((a, b) => a + b);
  final out = Float64List(x.length);
  for (var i = 0; i < x.length; i++) {
    var acc = 0.0;
    for (var j = -r; j <= r; j++) {
      final idx = (i + j).clamp(0, x.length - 1);
      acc += x[idx] * k[j + r];
    }
    out[i] = acc / ks;
  }
  return out;
}

/// Moving average, np.convolve(x, ones(n)/n, mode='same').
Float64List movingAverageSame(List<double> x, int n) {
  final out = Float64List(x.length);
  final half = (n - 1) ~/ 2; // numpy 'same' centre for even/odd kernels
  final pre = Float64List(x.length + 1);
  for (var i = 0; i < x.length; i++) {
    pre[i + 1] = pre[i] + x[i];
  }
  for (var i = 0; i < x.length; i++) {
    final a = math.max(0, i - (n - 1 - half));
    final b = math.min(x.length - 1, i + half);
    out[i] = (pre[b + 1] - pre[a]) / n;
  }
  return out;
}
