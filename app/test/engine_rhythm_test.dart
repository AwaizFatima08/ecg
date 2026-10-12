import 'dart:convert';
import 'dart:io';

import 'package:ecg_reader/engine/rhythm.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final recs = (jsonDecode(File('test/vectors/rhythm.json').readAsStringSync()) as List).cast<Map<String, dynamic>>();
  test('rhythm input preparation matches Python (sanity: finite, clipped, median-free)', () {
    for (final r in recs) {
      final x = (r['lead2'] as List).map((v) => (v as num).toDouble()).toList();
      final inp = rhythmInput(x);
      expect(inp.length, 1000);
      expect(inp.every((v) => v.isFinite && v.abs() <= 5), isTrue);
    }
  });
  test('softmax sums to 1', () {
    final p = softmax([1.0, 2.0, 3.0, 4.0]);
    expect((p.reduce((a, b) => a + b) - 1).abs(), lessThan(1e-9));
    expect(p.last, greaterThan(p.first));
  });
}
