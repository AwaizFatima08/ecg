import 'dart:convert';
import 'dart:io';

import 'package:ecg_reader/engine/dsp.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final v = jsonDecode(File('test/vectors/dsp.json').readAsStringSync()) as Map<String, dynamic>;
  List<double> d(String k) => (v[k] as List).map((e) => (e as num).toDouble()).toList();
  void close(List<double> a, List<double> b, double tol) {
    expect(a.length, b.length);
    for (var i = 0; i < a.length; i++) {
      expect((a[i] - b[i]).abs(), lessThan(tol), reason: 'index $i: ${a[i]} vs ${b[i]}');
    }
  }

  test('filtfilt matches scipy (both bands)', () {
    close(Band.qrs.apply(d('x')), d('filtfilt_qrs'), 1e-9);
    close(Band.pWave.apply(d('x')), d('filtfilt_p'), 1e-9);
    close(Band.qrsHf.apply(d('x')), d('filtfilt_hf'), 1e-9);
  });
  test('find_peaks matches scipy', () {
    final e = d('e');
    final sorted = [...e]..sort();
    final p98 = _percentile(sorted, 98);
    expect(findPeaks(e, distance: 25, height: p98 * 0.4), (v['peaks_height_distance'] as List).cast<int>());
    expect(findPeaks(d('x'), distance: 20, prominence: 0.3), (v['peaks_prominence'] as List).cast<int>());
  });
  test('polyfit2 matches numpy', () => close(polyfit2(d('poly_x'), d('poly_y')), d('poly_c'), 1e-7));
  test('gaussian smoothing matches', () => close(gaussianSmooth(d('x'), (v['gauss_sigma'] as num).toDouble()), d('gauss'), 1e-9));
  test('moving average same matches numpy (odd and even n)', () {
    close(movingAverageSame(d('x'), v['movavg_n'] as int), d('movavg'), 1e-9);
    close(movingAverageSame(d('x'), v['movavg_n2'] as int), d('movavg2'), 1e-9);
  });
}

/// numpy percentile (linear interpolation) on a sorted list.
double _percentile(List<double> s, double q) {
  final pos = (s.length - 1) * q / 100;
  final lo = pos.floor(), hi = pos.ceil();
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}
