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
}
