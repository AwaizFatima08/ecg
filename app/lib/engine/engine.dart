// On-device ECG reading engine. Nothing leaves the phone.
//   photo -> U-Net (segmenter) -> digitizer -> 12-lead signal
//         -> measurements + classifier -> structured reading -> alert rules
// The reading format and the label mapping match validation/engine_e2e.py, which is how
// the engine was validated on the Phase 0 set (see docs/engine-plan.md).
import 'package:flutter/foundation.dart';

import '../models/clinical_context.dart';
import '../models/ecg_result.dart';
import 'classifier.dart';
import 'digitizer.dart';
import 'measure.dart';
import 'rhythm.dart';
import 'rules.dart';
import 'segmenter.dart';

const engineVersion = 'on-device engine v13c (2026-10-22)';
const rulesVersion = '2026-10-12.1-proposed';

/// U-Net tile size in px (multiple of 128). 2048 = whole image at our 1600-px working size;
/// tiling trades accuracy for memory (see docs/engine-plan.md, tiling experiment 13 Oct 2026).
const segTile = 2048;

/// Classifier label -> (kind, finding/rhythm code, category, display name). Same table as engine_e2e.MAP.
const _map = <String, (String, String, String, String)>{
  'st_elevation_injury': ('finding', 'stemi_pattern', 'st_elevation', 'ST elevation (injury pattern)'),
  'acute_or_recent_mi': ('finding', 'stemi_pattern', 'st_elevation', 'Acute / recent infarction pattern'),
  'old_mi_q_waves': ('finding', 'pathological_q_waves', 'other', 'Q waves / old infarction pattern'),
  'st_depression_ischaemia': ('finding', 'st_depression', 'st_depression', 'ST depression / ischaemia'),
  't_wave_abnormality': ('finding', 't_wave_inversion', 't_wave', 'T-wave abnormality'),
  'atrial_fibrillation': ('rhythm', 'atrial_fibrillation', 'rhythm', 'Atrial fibrillation'),
  'atrial_flutter': ('rhythm', 'atrial_flutter', 'rhythm', 'Atrial flutter'),
  'svt': ('rhythm', 'svt', 'rhythm', 'Supraventricular tachycardia'),
  'pvcs': ('finding', 'pvcs', 'rhythm', 'Ventricular ectopics'),
  'pacs': ('finding', 'pacs', 'rhythm', 'Atrial ectopics'),
  'first_degree_av_block': ('finding', 'first_degree_av_block', 'conduction', 'First-degree AV block'),
  'second_or_third_degree_av_block': ('finding', 'high_grade_av_block', 'conduction', 'Second/third-degree AV block'),
  'lbbb': ('finding', 'lbbb', 'conduction', 'Left bundle branch block'),
  'rbbb': ('finding', 'rbbb', 'conduction', 'Right bundle branch block'),
  'left_anterior_fascicular_block': ('finding', 'left_anterior_fascicular_block', 'conduction', 'Left anterior fascicular block'),
  'nonspecific_ivcd': ('finding', 'nonspecific_ivcd', 'conduction', 'Intraventricular conduction delay'),
  'wpw_preexcitation': ('finding', 'wpw_preexcitation', 'conduction', 'Pre-excitation (WPW)'),
  'long_qt': ('finding', 'long_qt', 'other', 'Long QT'),
  'lvh': ('finding', 'lvh', 'other', 'Left ventricular hypertrophy'),
  'rvh': ('finding', 'rvh', 'other', 'Right ventricular hypertrophy'),
  'paced_rhythm': ('rhythm', 'paced_rhythm', 'rhythm', 'Paced rhythm'),
  'low_voltage': ('finding', 'low_voltage', 'other', 'Low QRS voltage'),
};

class EngineException implements Exception {
  EngineException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Builds the structured reading from the digitized signal, measurements, classifier output and
/// (optionally) the lethal-rhythm check. Same logic as validation/engine_e2e.py.
Map<String, dynamic> buildReading(Measurements m, Map<String, double> p, Map<String, double> thr,
    [RhythmResult? rhythmCheck, StMorphology? stm, bool noStrip = false]) {
  final bpm = m.rateBpm;
  final regular = m.rrRegular;
  final rconf = bpm != null && regular == true ? 0.8 : (bpm != null ? 0.6 : 0.0);
  final findings = <Map<String, dynamic>>[];
  Map<String, dynamic>? rhythm;
  final fired = <String>{};
  for (final e in p.entries) {
    final n = e.key;
    if (n == 'normal' || e.value < (thr[n] ?? 0.5)) continue;
    final spec = _map[n];
    if (spec == null) continue;
    fired.add(n);
    final (kind, code, cat, name) = spec;
    final conf = (0.5 + 0.5 * e.value).clamp(0.0, 0.95);
    if (kind == 'rhythm') {
      if (rhythm == null || conf > (rhythm['confidence'] as double)) {
        rhythm = {'code': code, 'label': name, 'regular': regular, 'confidence': conf};
      }
    } else {
      findings.add({'code': code, 'name': name, 'leads': <String>[], 'category': cat, 'confidence': conf});
    }
  }
  final afLike = fired.contains('atrial_fibrillation') || fired.contains('atrial_flutter');
  // Homi, 21 Oct 2026: an old infarct is not an emergency — Q/QS with persistent ST elevation, inverted T and no
  // reciprocal depression is URGENT, not CRITICAL (same logic as engine_e2e.py / st_morph.py).
  if (stm != null && stm.chronicPattern && findings.any((f) => f['code'] == 'stemi_pattern')) {
    findings.removeWhere((f) => f['code'] == 'stemi_pattern');
    findings.add({
      'code': 'old_mi_persistent_st_elevation', 'category': 'st_elevation', 'leads': <String>[], 'confidence': 0.6,
      'name': 'Q waves with persistent ST elevation (old infarct / aneurysm pattern)',
    });
  }
  // Lethal-rhythm check on the lead II strip: any of VT / VF / asystole is CRITICAL, so the alarm fires on
  // P(lethal) >= threshold and names the most likely one (the subtype itself is less reliable).
  if (rhythmCheck != null && rhythmCheck.pLethal >= 0.5) {
    const codes = {'vt': 'ventricular_tachycardia', 'vf': 'ventricular_fibrillation', 'asystole': 'asystole'};
    rhythm = {
      'code': codes[rhythmCheck.lethalClass] ?? 'ventricular_tachycardia',
      'label': 'Possible VT / VF or asystole (lethal-rhythm check)',
      'regular': regular,
      'confidence': rhythmCheck.pLethal.clamp(0.0, 0.95),
    };
  }
  final slow = bpm != null && bpm < 55;
  // [Homi approved 13 Oct 2026] a slow (< 55), regular ventricular rhythm with more P waves than QRS is a high-grade /
  // complete block even when the classifier also calls AF, provided the P waves are regular (fibrillatory waves are not);
  // the AF call only suppresses the faster, second-degree case. Same logic as engine_e2e.py.
  if (m.avBlockSuspected && !noStrip && (!afLike || (slow && m.atriaRegular == true))) {
    // [Homi approved 13 Oct 2026] a slow ventricular rate (< 55) makes a high-grade/complete block likely -> CRITICAL.
    findings.add({
      'code': slow ? 'high_grade_av_block' : 'second_degree_av_block_mobitz2',
      'category': 'conduction', 'leads': ['II'], 'confidence': 0.6,
      'name': 'Possible ${slow ? 'high-grade / complete' : 'second-degree'} AV block '
          '(atrial rate ${m.atrialRateBpm}, ventricular $bpm/min)',
    });
  }
  var qtc = m.qtcMs;
  if (qtc != null && qtc >= 470 && !fired.contains('long_qt')) qtc = null;
  if (findings.isEmpty && rhythm == null && (p['normal'] ?? 1) < (thr['normal'] ?? 0.5)) {
    findings.add({
      'code': 'other', 'category': 'other', 'leads': <String>[], 'confidence': 0.6,
      'name': 'Abnormal-looking ECG without a specific pattern identified — review it yourself',
    });
  }
  if (rhythm == null) {
    var code = 'sinus_rhythm';
    if (bpm != null && bpm > 100) code = 'sinus_tachycardia';
    if (bpm != null && bpm < 60) code = 'sinus_bradycardia';
    final label = code.replaceAll('_', ' ');
    rhythm = {'code': code, 'label': label[0].toUpperCase() + label.substring(1), 'regular': regular, 'confidence': 0.6};
  }
  return {
    'image_quality': {'readable': true, 'issues': <String>[], 'confidence': 0.8},
    'calibration': {'paper_speed_mm_s': null, 'gain_mm_mv': null, 'assumed': true},
    'layout': '12-lead standard',
    'rate_bpm': {'value': bpm, 'confidence': rconf},
    'rhythm': rhythm,
    'intervals': {
      'pr_ms': afLike ? null : m.prMs,
      'qrs_ms': m.qrsMs,
      'qt_ms': qtc != null ? m.qtMs : null,
      'qtc_ms': qtc,
    },
    'axis': {'label': m.axisLabel ?? 'cannot_assess', 'confidence': m.axisLabel != null ? 0.7 : 0.0},
    'findings': findings,
    'model_notes': 'Read on this phone: digitized trace, classifier, rule-based intervals/axis and AV-block check. '
        'Calibration assumed 25 mm/s, 10 mm/mV.',
  };
}

Map<String, dynamic> unreadableReading(String why) => {
      'image_quality': {'readable': false, 'issues': ['other'], 'confidence': 0.1},
      'calibration': {'paper_speed_mm_s': null, 'gain_mm_mv': null, 'assumed': true},
      'layout': 'other',
      'rate_bpm': {'value': null, 'confidence': 0},
      'rhythm': {'code': 'cannot_assess', 'label': 'Cannot assess', 'regular': null, 'confidence': 0},
      'intervals': {'pr_ms': null, 'qrs_ms': null, 'qt_ms': null, 'qtc_ms': null},
      'axis': {'label': 'cannot_assess', 'confidence': 0},
      'findings': <Map<String, dynamic>>[],
      'model_notes': 'The trace could not be extracted: $why. Supported: standard 12-lead 3x4 print with a lead II rhythm strip.',
    };

// Isolate entry: digitize + measure (pure Dart, CPU heavy).
Map<String, Object?> _digitizeAndMeasure((Map2D, Map2D) maps) {
  final res = postprocess(maps.$1, maps.$2);
  if (res.leads == null) return {'error': res.error};
  // 3x4 print without a lead II rhythm strip: lead II holds only its 2.5 s column (engine_e2e.py no_strip)
  final lead2 = res.leads![1];
  var nanII = 0;
  for (final v in lead2) {
    if (v.isNaN) nanII++;
  }
  final noStrip = nanII > lead2.length ~/ 2;
  final x = fillGaps(res.leads!);
  if (noStrip) {
    for (var i = 250; i < 1000; i++) {
      x[1][i] = 0.0; // blank the padded part so the classifier does not see a flat line
    }
  }
  final xm = noStrip ? [x[0], [for (var k = 0; k < 4; k++) ...x[1].sublist(0, 250)], ...x.sublist(2)] : x;
  return {'x': x, 'm': measure(xm), 'stm': stMorphology(xm), 'noStrip': noStrip};
}

class EcgEngine {
  EcgEngine._();
  static final instance = EcgEngine._();

  Segmenter? _seg;
  Classifier? _clf;
  RhythmModel? _rhythm;

  Future<void> _ensureLoaded() async {
    _seg ??= await Segmenter.load();
    _clf ??= await Classifier.load();
    _rhythm ??= await RhythmModel.load();
  }

  /// Reads one prepared ECG photo (JPEG bytes, long side 1600 px).
  Future<EcgResult> interpret(Uint8List jpeg, {void Function(String)? onStep}) async {
    try {
      await _ensureLoaded();
    } catch (e) {
      throw EngineException('The reading engine could not start on this phone.');
    }
    onStep?.call('Preparing the image…');
    final t = await compute(_prepare, jpeg);
    onStep?.call('Finding the ECG trace…');
    final maps = await _seg!.run(t, tile: segTile);
    onStep?.call('Reading the trace…');
    final dm = await compute(_digitizeAndMeasure, maps);
    Map<String, dynamic> reading;
    if (dm['error'] != null) {
      reading = unreadableReading(dm['error'] as String);
    } else {
      onStep?.call('Checking for patterns…');
      final x = dm['x'] as List<List<double>>;
      final p = await _clf!.predict(x);
      final m = dm['m'] as Measurements;
      final noStrip = dm['noStrip'] as bool;
      RhythmResult? rc = noStrip ? null : await _rhythm!.predict(x[1]); // the lethal-rhythm model needs the 10 s strip
      // lethal-rhythm gate (21 Oct 2026): the lethal class must beat "other" and the beat detector must not contradict it
      if (rc != null && rc.pLethal >= 0.5 &&
          (rc.probs[rc.classes.indexOf(rc.lethalClass)] <= rc.probs[0] || !lethalPlausible(x[1], rc.lethalClass, m.qrsMs))) {
        rc = null;
      }
      reading = buildReading(m, p, _clf!.thresholds, rc, dm['stm'] as StMorphology?, noStrip);
      if (noStrip) {
        reading['model_notes'] = '${reading['model_notes']} No lead II rhythm strip on this print: rhythm checks limited to 2.5 s.';
      }
    }
    final ev = evaluateEcg(reading);
    return EcgResult.fromResponse({
      'reading': reading,
      'alert': {'tier': ev.tier, 'reasons': [for (final r in ev.reasons) r.toJson()]},
      'model': engineVersion,
      'promptVersion': 'n/a',
      'rulesVersion': rulesVersion,
    });
  }

  ContextAssessment reassess(EcgResult result, ClinicalContext ctx) {
    final ev = evaluateWithContext(result.readingJson, ctx.toJson());
    return ContextAssessment.fromResponse({
      'tier': ev.tier,
      'ecgTier': ev.ecgTier,
      'escalations': [for (final e in ev.escalations) e.toJson()],
    });
  }
}

PreparedTensor _prepare(Uint8List jpeg) => prepareImage(jpeg);
