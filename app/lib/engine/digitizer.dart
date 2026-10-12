// Lite ECG digitizer, post-processing part: a port of postprocess() in
// validation/lite_digitizer.py. Input = signal and grid probability maps from the
// segmentation U-Net (see segmenter.dart); output = 12 leads x 1000 samples (mV, 100 Hz),
// NaN where a lead is not printed. Supports the standard 3x4 + lead II rhythm-strip print.
import 'dart:math' as math;
import 'dart:typed_data';

import 'dsp.dart';
import 'measure.dart' show pyRound;

const leadNames = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
const _grid3x4 = [
  ['I', 'aVR', 'V1', 'V4'],
  ['II', 'aVL', 'V2', 'V5'],
  ['III', 'aVF', 'V3', 'V6'],
];

/// A row-major float image.
class Map2D {
  Map2D(this.w, this.h, [Float32List? data]) : d = data ?? Float32List(w * h);
  final int w, h;
  final Float32List d;
  double at(int x, int y) => d[y * w + x];

  Float64List rowSums([int y0 = 0, int? y1]) {
    final out = Float64List((y1 ?? h) - y0);
    for (var y = y0; y < (y1 ?? h); y++) {
      var s = 0.0;
      final o = y * w;
      for (var x = 0; x < w; x++) {
        s += d[o + x];
      }
      out[y - y0] = s;
    }
    return out;
  }

  Float64List colSums([int y0 = 0, int? y1]) {
    final out = Float64List(w);
    for (var y = y0; y < (y1 ?? h); y++) {
      final o = y * w;
      for (var x = 0; x < w; x++) {
        out[x] += d[o + x];
      }
    }
    return out;
  }
}

class DigitizeResult {
  DigitizeResult(this.leads, this.info, [this.error]);
  final List<Float64List>? leads;
  final Map<String, Object?> info;
  final String? error;
}

/// Bilinear rotation about the centre with zero fill (cv2.getRotationMatrix2D + warpAffine).
Map2D rotate(Map2D m, double angleDeg) {
  if (angleDeg == 0) return Map2D(m.w, m.h, Float32List.fromList(m.d));
  final a = math.cos(angleDeg * math.pi / 180), b = math.sin(angleDeg * math.pi / 180);
  final cx = m.w / 2, cy = m.h / 2;
  // forward: x' = a x + b y + tx ; y' = -b x + a y + ty  -> inverse for sampling
  final tx = (1 - a) * cx - b * cy, ty = b * cx + (1 - a) * cy;
  final out = Map2D(m.w, m.h);
  for (var y = 0; y < m.h; y++) {
    for (var x = 0; x < m.w; x++) {
      final dx = x - tx, dy = y - ty;
      final sx = a * dx - b * dy, sy = b * dx + a * dy;
      final x0 = sx.floor(), y0 = sy.floor();
      if (x0 < -1 || y0 < -1 || x0 >= m.w || y0 >= m.h) continue;
      final fx = sx - x0, fy = sy - y0;
      double px(int xx, int yy) => (xx < 0 || yy < 0 || xx >= m.w || yy >= m.h) ? 0.0 : m.d[yy * m.w + xx];
      out.d[y * m.w + x] = (px(x0, y0) * (1 - fx) + px(x0 + 1, y0) * fx) * (1 - fy) +
          (px(x0, y0 + 1) * (1 - fx) + px(x0 + 1, y0 + 1) * fx) * fy;
    }
  }
  return out;
}

Map2D _half(Map2D m) {
  final w = m.w ~/ 2, h = m.h ~/ 2;
  final out = Map2D(w, h);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      out.d[y * w + x] = (m.at(2 * x, 2 * y) + m.at(2 * x + 1, 2 * y) + m.at(2 * x, 2 * y + 1) + m.at(2 * x + 1, 2 * y + 1)) / 4;
    }
  }
  return out;
}

double bestRotation(Map2D grid) {
  final small = _half(grid);
  double score(double a) {
    final r = rotate(small, a);
    return variance(r.rowSums()) + variance(r.colSums());
  }

  double best(Iterable<double> angles) {
    var bestA = angles.first, bestS = -1.0;
    for (final a in angles) {
      final s = score(a);
      if (s > bestS) {
        bestS = s;
        bestA = a;
      }
    }
    return bestA;
  }

  final coarse = best([for (var a = -8.0; a <= 8.0; a += 1.0) a]);
  return best([for (var k = 0; k <= 6; k++) coarse - 0.75 + 0.25 * k]);
}

double gridPeriod(Map2D grid, double prior) {
  final ests = <double>[];
  final lo = (5 * prior * 0.75).toInt(), hi = (5 * prior * 1.25).ceil();
  for (final prof0 in [grid.colSums(), grid.rowSums()]) {
    final m = mean(prof0);
    final prof = [for (final v in prof0) v - m];
    final n = prof.length;
    if (hi + 1 >= n || lo < 2) continue;
    double ac(int lag) {
      var s = 0.0;
      for (var i = 0; i + lag < n; i++) {
        s += prof[i] * prof[i + lag];
      }
      return s;
    }

    final a0 = ac(0) + 1e-9;
    final acs = <int, double>{for (var l = lo - 1; l <= hi + 1; l++) l: ac(l) / a0};
    var lag = lo;
    for (var l = lo; l <= hi; l++) {
      if (acs[l]! > acs[lag]!) lag = l;
    }
    if (acs[lag]! < 0.05 || lag == lo || lag == hi) continue;
    var lagF = lag.toDouble();
    final d = acs[lag - 1]! - 2 * acs[lag]! + acs[lag + 1]!;
    if (d < 0) lagF = lag + 0.5 * (acs[lag - 1]! - acs[lag + 1]!) / d;
    ests.add(lagF / 5);
  }
  return ests.isEmpty ? prior : median(ests);
}

/// Quadratic pixel->mm map from the 5 mm major grid lines in a band profile (null if not found).
List<double>? ruler(List<double> profile, double ppm) {
  final n = math.max(3, (10 * ppm).toInt());
  final ma = movingAverageSame(profile, n);
  final p = [for (var i = 0; i < profile.length; i++) profile[i] - ma[i]];
  final pk = findPeaks(p, distance: math.max(2, (3.5 * ppm).toInt()), prominence: math.max(1e-6, 0.15 * std(p)));
  if (pk.length < 6) return null;
  final step = median([for (var i = 1; i < pk.length; i++) (pk[i] - pk[i - 1]).toDouble()]);
  if (!(3.5 * ppm < step && step < 6.5 * ppm)) return null;
  final idx = <int>[0], xs = <double>[pk[0].toDouble()];
  for (final q in pk.skip(1)) {
    final k = pyRound((q - xs.last) / step);
    if (k < 1) continue;
    idx.add(idx.last + k);
    xs.add(q.toDouble());
  }
  final mm = [for (final i in idx) 5.0 * i];
  var c = polyfit2(xs, mm);
  final keepX = <double>[], keepY = <double>[];
  for (var i = 0; i < xs.length; i++) {
    if ((polyval(c, xs[i]) - mm[i]).abs() < 1.5) {
      keepX.add(xs[i]);
      keepY.add(mm[i]);
    }
  }
  if (keepX.length >= 6) c = polyfit2(keepX, keepY);
  return c;
}

DigitizeResult postprocess(Map2D sig0, Map2D grid0) {
  final info = <String, Object?>{};
  final h = sig0.h;
  final ang = bestRotation(grid0);
  info['rotation_deg'] = ang;
  final sig = rotate(sig0, ang), grid = rotate(grid0, ang);

  final colS = sig.colSums();
  final colMax = colS.reduce(math.max);
  final cols = [for (var x = 0; x < colS.length; x++) if (colS[x] > colMax * 0.05) x];
  if (cols.length < 10) return DigitizeResult(null, info, 'no trace found');
  final prior = (cols.last - cols.first) / 258.0;
  final ppm = gridPeriod(grid, prior);
  info['px_per_mm'] = ppm;
  if (ppm < 2) return DigitizeResult(null, info, 'grid not found');

  final prof = gaussianSmooth(sig.rowSums(), math.max(1.0, 2.5 * ppm));
  final profMax = prof.reduce(math.max);
  var pk = findPeaks(prof, distance: math.max(3, (15 * ppm).toInt()), prominence: profMax * 0.05);
  if (pk.length < 4) return DigitizeResult(null, info, 'found ${pk.length} rows, need 4');
  final byProm = [...pk]..sort((a, b) => peakProminence(prof, a).compareTo(peakProminence(prof, b)));
  pk = byProm.sublist(byProm.length - 4)..sort();
  info['rows_y'] = pk;
  final bounds = [0, for (var i = 0; i < 3; i++) (pk[i] + pk[i + 1]) ~/ 2, h];

  final out = List<Float64List>.generate(12, (_) => Float64List(1000)..fillRange(0, 1000, double.nan));
  final totalPx = 250 * ppm;
  final rb = sig.colSums(bounds[3], bounds[4]);
  final rbMax = rb.reduce(math.max);
  final on = [for (var x = 0; x < rb.length; x++) if (rb[x] > rbMax * 0.08) x];
  if (on.length < 10) return DigitizeResult(null, info, 'rhythm strip not found');
  final x1Glob = on.last;
  final x0Glob = math.max(0, pyRound(x1Glob - totalPx));
  info['x_range'] = [x0Glob, x1Glob];
  final r = ruler(grid.colSums(bounds[3], bounds[4]), ppm);
  final endMmR = r == null ? null : polyval(r, x1Glob.toDouble());
  info['ruler'] = r != null;
  final xc = (x0Glob + x1Glob) / 2;
  final ti = [for (var i = 0; i < 1000; i++) i / 100.0];

  for (var row = 0; row < 4; row++) {
    final y0b = bounds[row], y1b = bounds[row + 1], bh = y1b - y0b;
    // centroid y per column and validity
    final yC = Float64List(sig.w), vmax = Float64List(sig.w);
    for (var x = 0; x < sig.w; x++) {
      var ws = 0.0, wy = 0.0, mx = 0.0;
      for (var y = y0b; y < y1b; y++) {
        final v = sig.d[y * sig.w + x];
        ws += v;
        wy += v * (y - y0b);
        if (v > mx) mx = v;
      }
      yC[x] = wy / (ws + 1e-9);
      vmax[x] = mx;
    }
    final b = r == null ? null : (row == 3 ? r : ruler(grid.colSums(y0b, y1b), ppm));
    late List<int> xs;
    late List<double> t;
    if (b != null) {
      final off = 5.0 * pyRound((polyval(r!, xc) - polyval(b, xc)) / 5.0);
      xs = [for (var x = 0; x < sig.w; x++) x];
      t = [for (final x in xs) (polyval(b, x.toDouble()) + off - (endMmR! - 250.0)) / 25.0];
    } else {
      xs = [for (var x = x0Glob; x <= x1Glob; x++) x];
      t = [for (final x in xs) (x - x0Glob) / (25 * ppm)];
    }
    // vertical scale from the band's horizontal grid lines
    final hc = ruler(grid.rowSums(y0b, y1b), ppm);
    var ppmY = hc != null ? (1.0 / polyderAt(hc, bh / 2)).abs() : ppm;
    if (!(0.7 * ppm < ppmY && ppmY < 1.4 * ppm)) ppmY = ppm;
    final validY = [for (final x in xs) if (vmax[x] > 0.15) yC[x]];
    final baseY = median(validY.isNotEmpty ? validY : [for (final x in xs) yC[x]]);
    final tOk = <double>[], vOk = <double>[];
    for (var i = 0; i < xs.length; i++) {
      if (vmax[xs[i]] > 0.15) {
        tOk.add(t[i]);
        vOk.add(-(yC[xs[i]] - baseY) / ppmY / 10.0);
      }
    }
    var samples = Float64List(1000)..fillRange(0, 1000, double.nan);
    if (tOk.length > 10) samples = interpNan(ti, tOk, vOk);
    if (row == 3) {
      out[1] = samples;
      continue;
    }
    for (var c = 0; c < 4; c++) {
      if (row == 1 && c == 0) continue;
      final j = leadNames.indexOf(_grid3x4[row][c]);
      final a = c * 250, e = (c + 1) * 250;
      final segVals = [for (var i = a; i < e; i++) samples[i]];
      final m = median(segVals);
      for (var i = a; i < e; i++) {
        out[j][i] = samples[i].isNaN ? double.nan : samples[i] - m;
      }
    }
  }
  return DigitizeResult(out, info);
}
