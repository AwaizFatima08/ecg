import 'package:ecg_reader/models/alert_tier.dart';
import 'package:ecg_reader/models/clinical_context.dart';
import 'package:ecg_reader/models/ecg_result.dart';
import 'package:flutter_test/flutter_test.dart';

// Shape returned by interpretEcg (functions/src/interpretEcg.ts).
final sample = <String, dynamic>{
  'reading': {
    'image_quality': {'readable': true, 'issues': ['glare'], 'confidence': 0.8},
    'calibration': {'paper_speed_mm_s': null, 'gain_mm_mv': null, 'assumed': true},
    'layout': '12-lead standard',
    'rate_bpm': {'value': 96, 'confidence': 0.85},
    'rhythm': {'code': 'sinus_rhythm', 'label': 'Sinus rhythm', 'regular': true, 'confidence': 0.9},
    'intervals': {'pr_ms': 160, 'qrs_ms': 90, 'qt_ms': 360, 'qtc_ms': 455},
    'axis': {'label': 'normal', 'confidence': 0.7},
    'findings': [
      {'code': 'st_depression', 'name': 'Reciprocal ST depression', 'leads': ['II', 'III', 'aVF'], 'category': 'st_depression', 'confidence': 0.7},
      {'code': 'stemi_pattern', 'name': 'ST elevation, anterior', 'leads': ['V2', 'V3'], 'category': 'st_elevation', 'confidence': 0.8},
    ],
    'model_notes': 'Calibration not visible.',
  },
  'alert': {
    'tier': 'CRITICAL',
    'reasons': [
      {'rule': 'F:stemi_pattern', 'tier': 'CRITICAL', 'text': 'ST elevation, anterior (V2, V3)'},
    ],
  },
  'model': 'claude-opus-5-5',
  'promptVersion': 'p1',
  'rulesVersion': 'r1',
};

void main() {
  test('parses interpretEcg response', () {
    final r = EcgResult.fromResponse(sample);
    expect(r.tier, AlertTier.critical);
    expect(r.reasons.single.text, contains('V2'));
    final rd = r.reading;
    expect(rd.rate, 96);
    expect(rd.calibrationAssumed, isTrue);
    expect(rd.qualityIssues, ['glare']);
    expect(rd.findings.first.code, 'stemi_pattern', reason: 'sorted by confidence');
    expect(rd.qtc, 455);
  });

  test('unknown tier falls back to UNREADABLE, never to a reassuring tier', () {
    expect(AlertTier.fromCode('SOMETHING_NEW'), AlertTier.unreadable);
    expect(AlertTier.fromCode(null), AlertTier.unreadable);
  });

  test('there is no NORMAL tier and severities match the rules engine', () {
    expect(AlertTier.values.map((t) => t.code), isNot(contains('NORMAL')));
    expect(AlertTier.critical.severity > AlertTier.urgent.severity, isTrue);
    expect(AlertTier.unreadable.severity > AlertTier.noCriticalPattern.severity, isTrue);
  });

  test('clinical context JSON matches the server schema', () {
    final c = ClinicalContext()
      ..age = 60
      ..sbp = 85
      ..complaints.addAll(['chest_pain'])
      ..chestPainOngoing = true
      ..complaintOther = '   ';
    final j = c.toJson();
    expect(j['complaints'], ['chest_pain']);
    expect(j['chest_pain_ongoing'], isTrue);
    expect(j['complaint_other'], isNull);
    expect(j.keys.toSet(), {
      'age', 'sex', 'complaints', 'complaint_other', 'chest_pain_ongoing',
      'sbp', 'dbp', 'heart_rate', 'spo2', 'conditions',
    });
  });

  test('missing fields do not crash parsing', () {
    final r = EcgResult.fromResponse({'reading': {}, 'alert': {}});
    expect(r.tier, AlertTier.unreadable);
    expect(r.reading.findings, isEmpty);
    expect(r.reading.rate, isNull);
  });
}
