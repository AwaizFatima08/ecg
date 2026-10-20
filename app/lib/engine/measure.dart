// Rule-based ECG measurements: a line-by-line port of validation/ecg_measure.py.
// Input: 12 leads x 1000 samples (mV, 100 Hz) in I II III aVR aVL aVF V1..V6 order, as
// recovered from a 3x4 print (lead II valid for 10 s, other leads only inside their 2.5 s column).
import 'dart:math' as math;
import 'dart:typed_data';

import 'dsp.dart';

const int fs = 100;
const List<int> column = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3];

class Measurements {
  int? rateBpm;
  bool? rrRegular;
  double? rrCv;
  int? prMs, qrsMs, qtMs, qtcMs, axisDeg;
  String? axisLabel;
  int? atrialRateBpm;
  double? conductionRatio;
  bool avBlockSuspected = false;
  bool? atriaRegular;
  final List<String> notes = [];

  Map<String, Object?> toJson() => {
        'rate_bpm': rateBpm, 'rr_regular': rrRegular, 'pr_ms': prMs, 'qrs_ms': qrsMs, 'qt_ms': qtMs,
        'qtc_ms': qtcMs, 'axis_deg': axisDeg, 'axis_label': axisLabel, 'atrial_rate_bpm': atrialRateBpm,
        'av_block_suspected': avBlockSuspected, 'atria_regular': atriaRegular,
      };
}

/// Python's round() (half to even).
int pyRound(double v) {
  final f = v.floorToDouble();
  final diff = v - f;
  if (diff > 0.5) return f.toInt() + 1;
  if (diff < 0.5) return f.toInt();
  return f.toInt().isEven ? f.toInt() : f.toInt() + 1;
}

Float64List gradient(List<double> x) {
  final n = x.length;
  final g = Float64List(n);
  if (n < 2) return g;
  g[0] = x[1] - x[0];
  g[n - 1] = x[n - 1] - x[n - 2];
  for (var i = 1; i < n - 1; i++) {
    g[i] = (x[i + 1] - x[i - 1]) / 2;
  }
  return g;
}

double percentile(List<double> v, double q) {
  final s = [...v]..sort();
  final pos = (s.length - 1) * q / 100;
  final lo = pos.floor(), hi = pos.ceil();
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}

int argmaxAbs(List<double> v) {
  var best = 0;
  for (var i = 1; i < v.length; i++) {
    if (v[i].abs() > v[best].abs()) best = i;
  }
  return best;
}

/// Second-pass R-peak gate (fraction of the median of the 5 strongest beats' 12-30 Hz slope energy).
const qrsGate = 0.4;

List<int> rPeaks(List<double> lead2) {
  final y = Band.qrs.apply(lead2);
  final e = gradient(y).map((v) => v.abs()).toList();
  var pk = findPeaks(e, distance: (0.25 * fs).toInt(), height: percentile(e, 98) * 0.4);
  if (pk.isEmpty) return pk;
  // Second pass (ecg_measure.r_peaks, 13 Oct 2026): keep detections whose 12-30 Hz slope energy is comparable to
  // the strongest beats, so tall P waves (complete heart block, slow escape rhythms) are not counted as beats.
  // Trust the first pass if that leaves too few or implausibly slow beats (a few large PVCs).
  final hf = gradient(Band.qrsHf.apply(lead2)).map((v) => v.abs()).toList();
  final hfp = [
    for (final p in pk) hf.sublist(math.max(0, p - 5), math.min(hf.length, p + 6)).reduce(math.max),
  ];
  final top = List<double>.from(hfp)..sort((a, b) => b.compareTo(a));
  final gate = qrsGate * median(top.sublist(0, math.min(5, top.length)));
  final keep = [for (var i = 0; i < pk.length; i++) if (hfp[i] >= gate) pk[i]];
  if (keep.length >= 3) {
    final d = [for (var i = 1; i < keep.length; i++) (keep[i] - keep[i - 1]).toDouble()];
    if (median(d) <= 2.0 * fs) pk = keep;
  }
  final med = median(lead2);
  final out = <int>{};
  for (final p in pk) {
    final a = math.max(0, p - 6), b = math.min(lead2.length, p + 7);
    final seg = [for (var i = a; i < b; i++) lead2[i] - med];
    out.add(a + argmaxAbs(seg));
  }
  return out.toList()..sort();
}

(int, int) _window(int j) => j == 1 ? (0, 1000) : (column[j] * 250, (column[j] + 1) * 250);

/// Median beat per lead around R (pre/post samples); null where a lead has no complete beat.
List<Float64List?> medianBeats(List<List<double>> x, List<int> r, int pre, int post) {
  final len = pre + post;
  return List.generate(12, (j) {
    final (w0, w1) = _window(j);
    final beats = [for (final p in r) if (p - pre >= w0 && p + post <= w1) x[j].sublist(p - pre, p + post)];
    if (beats.isEmpty) return null;
    final m = Float64List(len);
    for (var k = 0; k < len; k++) {
      m[k] = median([for (final b in beats) b[k]]);
    }
    final base = median(m.sublist(0, 10));
    for (var k = 0; k < len; k++) {
      m[k] -= base;
    }
    return m;
  });
}

Measurements measure(List<List<double>> x) {
  final res = Measurements();
  final r = rPeaks(x[1]);
  if (r.length < 3) {
    res.notes.add('too few beats on lead II');
    return res;
  }
  final rr = <double>[];
  for (var i = 1; i < r.length; i++) {
    final d = (r[i] - r[i - 1]) / fs;
    if (d > 0.25 && d < 2.5) rr.add(d);
  }
  if (rr.length < 2) return res;
  final rrMed = median(rr);
  final cv = std(rr) / mean(rr);
  res.rateBpm = pyRound(60 / rrMed);
  res.rrRegular = cv < 0.12;
  res.rrCv = cv;

  const pre = 35, post = 60;
  final mb = medianBeats(x, r, pre, post);
  final validLeads = [for (var j = 0; j < 12; j++) if (mb[j] != null) j];
  if (validLeads.length < 3) {
    res.notes.add('too few leads with complete beats');
    return res;
  }
  // QRS onset/offset from spatial velocity across available leads
  final velRaw = Float64List(pre + post - 1);
  for (var k = 0; k < velRaw.length; k++) {
    var s = 0.0;
    for (final j in validLeads) {
      final d = mb[j]![k + 1] - mb[j]![k];
      s += d * d;
    }
    velRaw[k] = math.sqrt(s);
  }
  final vel = movingAverageSame(velRaw, 2);
  var peak = pre - 8;
  for (var k = pre - 8; k < pre + 8; k++) {
    if (vel[k] > vel[peak]) peak = k;
  }
  final thr = 0.30 * vel[peak] + median(vel.sublist(0, 15)); // calibrated for digitized traces (see ecg_measure.py)
  var on = peak;
  while (on > 5 && vel[on - 1] > thr) {
    on--;
  }
  var off = peak;
  while (off < vel.length - 2 && vel[off + 1] > thr) {
    off++;
  }
  off++;
  final qrs = (off - on) * 1000 / fs;
  if (qrs >= 40 && qrs <= 220) res.qrsMs = pyRound(qrs);

  final ii = mb[1];
  if (ii != null) {
    final base5 = median(ii.sublist(0, 5));
    final a = math.max(0, on - 30), b = math.max(0, on - 5);
    if (b - a > 5) {
      final seg = [for (var i = a; i < b; i++) ii[i] - base5];
      final pIdx = a + argmaxAbs(seg);
      final pAmp = (ii[pIdx] - base5).abs();
      var qrsAmp = 0.0;
      for (var i = on; i < off; i++) {
        qrsAmp = math.max(qrsAmp, ii[i].abs());
      }
      if (qrsAmp > 0 && pAmp > 0.04 && pAmp < 0.6 * qrsAmp) {
        var ponset = pIdx;
        while (ponset > 0 && (ii[ponset - 1] - base5).abs() > 0.2 * pAmp) {
          ponset--;
        }
        final pr = (on - ponset) * 1000 / fs;
        if (pr >= 80 && pr <= 400) res.prMs = pyRound(pr);
      }
    }
    // T end on lead II, tangent method on a longer median beat
    final longPost = math.min((rrMed * fs).toInt() - 10, 70);
    final beats = [for (final p in r) if (p - pre >= 0 && p + longPost <= 1000) x[1].sublist(p - pre, p + longPost)];
    if (beats.length >= 2 && longPost > 30) {
      final n = pre + longPost;
      final lb = Float64List(n);
      for (var k = 0; k < n; k++) {
        lb[k] = median([for (final bt in beats) bt[k]]);
      }
      final base = median(lb.sublist(0, 10));
      for (var k = 0; k < n; k++) {
        lb[k] -= base;
      }
      final t0 = off + 8;
      if (t0 < n - 5) {
        final tp = t0 + argmaxAbs(lb.sublist(t0));
        if (lb[tp].abs() > 0.05) {
          final d = gradient(lb);
          final k = tp < n - 2 ? tp + argmaxAbs(d.sublist(tp)) : tp;
          final slope = d[k];
          if (slope.abs() > 1e-4) {
            final tend = k - lb[k] / slope;
            final qt = (tend - on) * 1000 / fs;
            if (qt >= 240 && qt <= 650) {
              res.qtMs = pyRound(qt);
              res.qtcMs = pyRound(qt / math.sqrt(rrMed));
            }
          }
        }
      }
    }
  }
  // Axis from net QRS area in I and aVF
  if (mb[0] != null && mb[5] != null) {
    var ni = 0.0, nf = 0.0;
    for (var i = on; i < off; i++) {
      ni += mb[0]![i];
      nf += mb[5]![i];
    }
    final ang = math.atan2(nf, ni) * 180 / math.pi;
    res.axisDeg = pyRound(ang);
    res.axisLabel = (ang >= -30 && ang <= 90)
        ? 'normal'
        : (ang >= -90 && ang < -30)
            ? 'left'
            : (ang > 90 && ang <= 180)
                ? 'right'
                : 'extreme';
  }
  if (ii != null) _avRelation(x[1], r, ii, on, off, pre, res);
  return res;
}

void _avRelation(List<double> lead2, List<int> r, List<double> beat, int on, int off, int pre, Measurements out) {
  final med = median(lead2);
  final resid = Float64List.fromList([for (final v in lead2) v - med]);
  final len = beat.length;
  for (final p in r) {
    final a = p - pre, b = p - pre + len;
    if (a >= 0 && b <= resid.length) {
      for (var i = 0; i < len; i++) {
        resid[a + i] -= beat[i];
      }
    }
  }
  for (final p in r) {
    final a = math.max(0, p - pre + on - 2), b = math.min(resid.length, p - pre + off + 2);
    for (var i = a; i < b; i++) {
      resid[i] = 0;
    }
  }
  final y = Band.pWave.apply(resid);
  final qrsAmp = percentile([for (final v in lead2) (v - med).abs()], 99);
  final h = math.max(0.04, 0.12 * qrsAmp);
  final pk = findPeaks([for (final v in y) v.abs()], distance: (0.3 * fs).toInt(), height: h, prominence: h * 0.7);
  if (pk.length < 4) return;
  final pp = <double>[];
  for (var i = 1; i < pk.length; i++) {
    final d = (pk[i] - pk[i - 1]) / fs;
    if (d > 0.3 && d < 2.0) pp.add(d);
  }
  if (pp.length < 3) return;
  final aRate = 60 / median(pp);
  final rrAll = [for (var i = 1; i < r.length; i++) (r[i] - r[i - 1]) / fs];
  final vRate = 60 / median(rrAll);
  final phases = <double>[];
  for (final q in pk) {
    final prev = r.where((v) => v < q).toList();
    if (prev.isNotEmpty && q - prev.last < 2.5 * fs) phases.add((q - prev.last) / fs);
  }
  var locked = false;
  if (phases.length >= 4) {
    final m = median(phases);
    locked = phases.where((p) => (p - m).abs() < 0.06).length / phases.length >= 0.6;
  }
  // PR for each QRS: last P within 0.6 s before R (ecg_measure.av_relation)
  final prs = <double>[];
  for (final q in r) {
    final before = [for (final p in pk) if (p < q - 4 && p > q - 60) p];
    if (before.isNotEmpty) prs.add((q - before.last) / fs);
  }
  final prSd = prs.length >= 3 ? std(prs) : 0.0;
  // Guard (21 Oct 2026): a conducted rhythm has a fixed PR, so a small PR sd means the extra "P" candidates are T waves.
  final conducted = prs.length >= 3 && prSd * 1000 <= 40;
  out.atrialRateBpm = pyRound(aRate);
  out.atriaRegular = std(pp) / mean(pp) < 0.15;
  out.conductionRatio = aRate / vRate;
  out.avBlockSuspected = aRate / vRate >= 1.4 && vRate < 70 && aRate >= 55 && aRate <= 150 && !locked && !conducted;
}

/// Fills NaN gaps the way validation/engine_e2e.load_digitized does: per lead, linear interpolation
/// between valid samples with constant extension at the ends (np.interp default).
List<List<double>> fillGaps(List<Float64List> x) {
  return [
    for (final lead in x)
      () {
        final idx = <double>[], val = <double>[];
        for (var i = 0; i < lead.length; i++) {
          if (!lead[i].isNaN) {
            idx.add(i.toDouble());
            val.add(lead[i]);
          }
        }
        if (idx.length <= 10) return List<double>.filled(lead.length, 0.0);
        final out = interpNan([for (var i = 0; i < lead.length; i++) i.toDouble()], idx, val);
        for (var i = 0; i < out.length; i++) {
          if (out[i].isNaN) out[i] = i < idx.first ? val.first : val.last;
        }
        return out.toList();
      }(),
  ];
}

/// Gate for the lethal-rhythm model (ecg_measure.lethal_plausible, 21 Oct 2026): a VT / VF / asystole call must be
/// consistent with what the beat detector sees on the lead II strip.
bool lethalPlausible(List<double> lead2, String cls, int? qrsMs) {
  final r = rPeaks(lead2);
  final n = r.length;
  final rr = <double>[];
  var gap = 10.0;
  if (n >= 2) {
    gap = 0;
    for (var i = 1; i < n; i++) {
      final d = (r[i] - r[i - 1]) / fs;
      if (d > gap) gap = d;
      if (d > 0.25 && d < 2.5) rr.add(d);
    }
  }
  final rate = rr.length >= 2 ? 60 / median(rr) : null;
  final cv = rr.length >= 2 ? std(rr) / mean(rr) : 1.0;
  final med = median(lead2);
  final amp = percentile([for (final v in lead2) (v - med).abs()], 99);
  if (cls == 'asystole') return n <= 4 || gap >= 2.0 || amp < 0.15; // flat strip: the beats found are noise
  final wide = qrsMs == null || qrsMs >= 110; // an organised narrow-QRS rhythm is neither VT nor VF
  if (cls == 'vf') return wide && cv >= 0.15; // VF is never a regular rhythm
  return wide && (rate == null || rate >= 90); // vt
}

