import 'dart:convert';
import 'dart:io';

import 'package:ecg_reader/engine/rules.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final cases = (jsonDecode(File('test/vectors/rules.json').readAsStringSync()) as List).cast<Map<String, dynamic>>();
  test('Dart rules give the same tiers and reasons as the TypeScript rules (${cases.length} cases)', () {
    for (final c in cases) {
      final r = Map<String, dynamic>.from(c['reading'] as Map);
      final e = evaluateEcg(r);
      expect(e.tier, c['ecg']['tier']);
      expect([for (final x in e.reasons) x.rule], (c['ecg']['rules'] as List).cast<String>());
      final w = evaluateWithContext(r, Map<String, dynamic>.from(c['context'] as Map));
      expect(w.tier, c['ctx']['tier']);
      expect([for (final x in w.escalations) x.rule], (c['ctx']['escalations'] as List).cast<String>());
    }
  });
}
