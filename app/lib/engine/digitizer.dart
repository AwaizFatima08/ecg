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

/// Pixel positions of the 5 mm major vertical lines in a band profile and their median spacing (null if not found).
(List<int>, double)? gridLines(List<double> profile, double ppm) {
  final n = math.max(3, (10 * ppm).toInt());
  final ma = movingAverageSame(profile, n);
  final p = [for (var i = 0; i < profile.length; i++) profile[i] - ma[i]];
  final pk = findPeaks(p, distance: math.max(2, (3.5 * ppm).toInt()), prominence: math.max(1e-6, 0.15 * std(p)));
  if (pk.length < 6) return null;
  final step = median([for (var i = 1; i < pk.length; i++) (pk[i] - pk[i - 1]).toDouble()]);
  if (!(3.5 * ppm < step && step < 6.5 * ppm)) return null;
  return (pk, step);
}

/// Quadratic fit with one outlier-rejection pass (lite_digitizer.ruler_from_lines).
List<double>? rulerFromLines(List<double> xs, List<double> mm) {
  if (xs.length < 6) return null;
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

/// Ruler plus the (xs, mm) lines it was fitted on: lines numbered step by step from the first one.
(List<double>, List<double>, List<double>)? rulerLines(List<double> profile, double ppm) {
  final g = gridLines(profile, ppm);
  if (g == null) return null;
  final (pk, step) = g;
  final idx = <int>[0], xs = <double>[pk[0].toDouble()];
  for (final q in pk.skip(1)) {
    final k = pyRound((q - xs.last) / step);
    if (k < 1) continue;
    idx.add(idx.last + k);
    xs.add(q.toDouble());
  }
  final mm = [for (final i in idx) 5.0 * i];
  final c = rulerFromLines(xs, mm);
  return c == null ? null : (c, xs, mm);
}

/// Quadratic pixel->mm map from the 5 mm major grid lines in a band profile (null if not found).
List<double>? ruler(List<double> profile, double ppm) => rulerLines(profile, ppm)?.$1;

/// Follows the rhythm strip's major lines upward through the grid map in thin slabs, so a tilted or keystoned
/// photo cannot swap a line for its neighbour (lite_digitizer.track_lines). Returns (slab centre y, xs, mm) per slab.
List<(int, List<double>, List<double>)> trackLines(
    Map2D grid, double ppm, List<double> xs0, List<double> mm0, int yFrom, int yTo) {
  final slabPx = math.max(8, (4 * ppm).toInt());
  final step = 5.0 * ppm;
  final cur = <double, double>{for (var i = 0; i < xs0.length; i++) mm0[i]: xs0[i]};
  final miss = <double, int>{for (final m in mm0) m: 0};
  final out = <(int, List<double>, List<double>)>[];
  var y = yFrom;
  final n = math.max(3, (10 * ppm).toInt());
  while (y - slabPx >= yTo) {
    final prof = grid.colSums(y - slabPx, y);
    final ma = movingAverageSame(prof, n);
    final p = [for (var i = 0; i < prof.length; i++) prof[i] - ma[i]];
    final pk = findPeaks(p, distance: math.max(2, (3.5 * ppm).toInt()), prominence: math.max(1e-6, 0.15 * std(p)));
    if (pk.isNotEmpty) {
      final keys = cur.keys.toList();
      final pos = [for (final k in keys) cur[k]!];
      var d0 = 0.0, best = -1;
      for (var d = -0.25 * step; d <= 0.25 * step + 0.5; d += 1.0) {
        var sc = 0;
        for (final x in pos) {
          var dist = double.infinity;
          for (final q in pk) {
            final dd = (q - (x + d)).abs();
            if (dd < dist) dist = dd;
          }
          if (dist < 0.15 * step) sc++;
        }
        if (sc > best) {
          best = sc;
          d0 = d;
        }
      }
      for (var i = 0; i < keys.length; i++) {
        final k = keys[i], x = pos[i];
        var j = 0;
        for (var q = 1; q < pk.length; q++) {
          if ((pk[q] - (x + d0)).abs() < (pk[j] - (x + d0)).abs()) j = q;
        }
        if ((pk[j] - (x + d0)).abs() < 0.25 * step) {
          cur[k] = pk[j].toDouble();
          miss[k] = 0;
        } else {
          cur[k] = x + d0;
          miss[k] = miss[k]! + 1;
        }
      }
    }
    for (final k in miss.keys.where((k) => miss[k]! > 6).toList()) {
      cur.remove(k);
      miss.remove(k);
    }
    y -= slabPx;
    final ks = cur.keys.toList()..sort((a, b) => cur[a]!.compareTo(cur[b]!));
    out.add((y + slabPx ~/ 2, [for (final k in ks) cur[k]!], ks));
  }
  return out;
}

/// Fraction of a band's height trimmed top and bottom for vertical-line profiles (tilted lines smear less).
const slab = 0.3;

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
  var pk = findPeaks(prof, distance: math.max(3, (8 * ppm).toInt()), prominence: profMax * 0.05);
  // Layout from the number of trace rows (lite_digitizer.postprocess): 4 = 3x4 + lead II strip, 3 = 3x4 without a
  // strip, 6 = 3x4 + three strips (strips ignored), 12 = 12x1 stacked leads. Faint extra rows are dropped at 35 %.
  final strong = [for (final p in pk) if (peakProminence(prof, p) >= profMax * 0.35) p];
  pk = ([3, 4, 6, 12].contains(strong.length) ? strong : pk)..sort();
  final n = pk.length;
  late final String layout;
  late final List<int> rows;
  int? stripIdx;
  if (n == 4) {
    layout = '3x4+1'; rows = [0, 1, 2]; stripIdx = 3;
  } else if (n == 3) {
    layout = '3x4'; rows = [0, 1, 2];
  } else if (n == 6) {
    layout = '3x4+3'; rows = [0, 1, 2];
  } else if (n == 12) {
    layout = '12x1'; rows = [for (var i = 0; i < 12; i++) i];
  } else {
    info['rows_found'] = n;
    return DigitizeResult(null, info, 'unsupported layout: found $n trace rows');
  }
  info['layout'] = layout;
  info['rows_y'] = pk;
  final mids = [for (var i = 0; i < n - 1; i++) (pk[i] + pk[i + 1]) ~/ 2];
  final bounds = layout == '3x4+3' ? [0, mids[0], mids[1], mids[2]] : [0, ...mids, h];
  final usedRows = [...rows, ?stripIdx];
  final ref = stripIdx ?? usedRows.last; // reference row for the time axis: the strip, else the last row

  final out = List<Float64List>.generate(12, (_) => Float64List(1000)..fillRange(0, 1000, double.nan));
  final totalPx = 250 * ppm;
  final rb = sig.colSums(bounds[ref], bounds[ref + 1]);
  final rbMax = rb.reduce(math.max);
  // Threshold must not scale with the tallest complex: a flat tail is only trace-thickness high (see lite_digitizer.py).
  final on = [for (var x = 0; x < rb.length; x++) if (rb[x] > math.max(0.5, rbMax * 0.02)) x];
  if (on.length < 10) return DigitizeResult(null, info, 'rhythm strip not found');
  final x1Glob = on.last;
  final x0Glob = math.max(0, pyRound(x1Glob - totalPx));
  info['x_range'] = [x0Glob, x1Glob];
  List<double> vprof(int a, int b) => grid.colSums(a + ((b - a) * slab).toInt(), b - ((b - a) * slab).toInt());
  final rl = rulerLines(vprof(bounds[ref], bounds[ref + 1]), ppm);
  final r = rl?.$1;
  final endMmR = r == null ? null : polyval(r, x1Glob.toDouble());
  info['ruler'] = r != null;
  final xc = (x0Glob + x1Glob) / 2;
  // Row rulers chained upward from the rhythm strip so every row shares its mm origin (see lite_digitizer.py).
  final chain = <int, List<double>>{};
  if (rl != null) {
    final tr = trackLines(grid, ppm, rl.$2, rl.$3, (bounds[ref] + bounds[ref + 1]) ~/ 2, 0);
    for (final row in usedRows.reversed.where((r) => r != ref)) {
      final ycRow = (bounds[row] + bounds[row + 1]) / 2;
      final half = (bounds[row + 1] - bounds[row]) * (0.5 - slab);
      final xs = <double>[], mm = <double>[];
      for (final (yy, xs_, mm_) in tr) {
        if ((yy - ycRow).abs() < half) {
          xs.addAll(xs_);
          mm.addAll(mm_);
        }
      }
      if (xs.length < 6) break;
      final c = rulerFromLines(xs, mm);
      if (c == null) break;
      chain[row] = c;
    }
  }
  info['chained_rows'] = chain.keys.toList()..sort();
  final ti = [for (var i = 0; i < 1000; i++) i / 100.0];

  for (final row in usedRows) {
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
    final b = r == null ? null : (row == ref ? r : (chain[row] ?? ruler(vprof(y0b, y1b), ppm)));
    late List<int> xs;
    late List<double> t;
    if (b != null) {
      // chained rows share the strip's origin; an unchained row falls back to whole-square alignment
      final off = (row == ref || chain.containsKey(row)) ? 0.0 : 5.0 * pyRound((polyval(r!, xc) - polyval(b, xc)) / 5.0);
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
    if (row == stripIdx) {
      out[1] = samples;
      continue;
    }
    if (layout == '12x1') {
      final vals = [for (final v in samples) if (!v.isNaN) v];
      final m = vals.isEmpty ? 0.0 : median(vals);
      for (var i = 0; i < 1000; i++) {
        out[row][i] = samples[i].isNaN ? double.nan : samples[i] - m;
      }
      continue;
    }
    for (var c = 0; c < 4; c++) {
      if (row == 1 && c == 0 && stripIdx != null) continue;
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
