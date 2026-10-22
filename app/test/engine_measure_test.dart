import 'dart:convert';
import 'dart:io';

import 'package:ecg_reader/engine/measure.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final recs = jsonDecode(File('test/vectors/measure.json').readAsStringSync()) as List;
  test('measurements match the Python reference on ${recs.length} digitized ECGs', () {
    var mismatches = 0;
    for (final r in recs.cast<Map<String, dynamic>>()) {
      final x = [for (final lead in r['x'] as List) [for (final v in lead as List) (v as num).toDouble()]];
      final got = measure(x).toJson();
      final want = r['m'] as Map<String, dynamic>;
      for (final k in want.keys) {
        final w = (k == 'av_block_suspected') ? (want[k] ?? false) : want[k];
        if (k == 'atria_regular' && want[k] == null) continue;
        if (got[k] != w) {
          mismatches++;
          // ignore: avoid_print
          print('${r['name']} $k: dart ${got[k]} python ${want[k]}');
        }
      }
    }
    expect(mismatches, 0);
  });

  test('ST morphology / chronic-pattern matches the Python reference', () {
    final recs = jsonDecode(File('test/vectors/measure.json').readAsStringSync()) as List;
    var n = 0;
    for (final r in recs.cast<Map<String, dynamic>>()) {
      final want = r['stm'] as Map<String, dynamic>?;
      if (want == null) continue;
      final x = [for (final lead in r['x'] as List) [for (final v in lead as List) (v as num).toDouble()]];
      final got = stMorphology(x);
      expect(got, isNotNull, reason: r['name'] as String);
      expect(got!.steLeads, (want['ste_leads'] as List).cast<int>(), reason: '${r['name']} ste_leads');
      expect((got.steFracQ - (want['ste_frac_q'] as num)).abs(), lessThan(1e-6), reason: '${r['name']} frac_q');
      expect((got.steFracTInv - (want['ste_frac_tinv'] as num)).abs(), lessThan(1e-6), reason: '${r['name']} frac_tinv');
      expect((got.recipMinSt - (want['recip_min_st'] as num)).abs(), lessThan(1e-6), reason: '${r['name']} recip');
      expect(got.chronicPattern, want['chronic'], reason: '${r['name']} chronic');
      n++;
    }
    expect(n, greaterThan(20));
  });
}
