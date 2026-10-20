import 'dart:convert';
import 'dart:io';

import 'package:ecg_reader/engine/measure.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('lethal-rhythm gate matches the Python reference', () {
    final vecs = (jsonDecode(File('test/vectors/lethal_gate.json').readAsStringSync()) as List).cast<Map<String, dynamic>>();
    for (final v in vecs) {
      final lead2 = (v['lead2'] as List).map((e) => (e as num).toDouble()).toList();
      expect(lethalPlausible(lead2, v['cls'] as String, v['qrs_ms'] as int?), v['plausible'], reason: '${v['name']} ${v['cls']}');
    }
  });
}
