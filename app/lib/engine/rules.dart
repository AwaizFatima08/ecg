// =============================================================================
//  ALERT RULES — on-device copy of functions/src/rules/alertRules.ts.
//  The TypeScript file is the reviewed source; this port must give identical
//  results (test/engine_rules_test.dart checks 320 cases generated from it).
//  When Homi changes a rule, change both files and regenerate the vectors:
//    cd functions && npx tsx scripts/makeRuleVectors.ts ../app/test/vectors/rules.json
// =============================================================================

typedef Json = Map<String, dynamic>;

const severity = {'NO_CRITICAL_PATTERN': 0, 'UNREADABLE': 1, 'ABNORMAL': 2, 'URGENT': 3, 'CRITICAL': 4};
const criticalMinConfidence = 0.3;
const otherMinConfidence = 0.5;
const minImageConfidence = 0.3;

const findingTiers = <String, String>{
  'stemi_pattern': 'CRITICAL', 'posterior_mi_pattern': 'CRITICAL', 'de_winter_pattern': 'CRITICAL',
  'diffuse_st_depression_with_avr_elevation': 'CRITICAL', 'third_degree_av_block': 'CRITICAL',
  'high_grade_av_block': 'CRITICAL', 'brugada_type1': 'CRITICAL', 'hyperkalaemia_pattern': 'CRITICAL',
  'st_elevation_not_meeting_stemi': 'URGENT', 'wellens_pattern': 'URGENT', 'hyperacute_t_waves': 'URGENT',
  'st_depression': 'URGENT', 'second_degree_av_block_mobitz2': 'URGENT', 'long_qt': 'URGENT', 'nsvt': 'URGENT',
  'sinus_pause': 'URGENT', 'electrical_alternans': 'URGENT', 'pericarditis_pattern': 'URGENT',
  'old_mi_persistent_st_elevation': 'URGENT',
  't_wave_inversion': 'ABNORMAL', 'pathological_q_waves': 'ABNORMAL', 'first_degree_av_block': 'ABNORMAL',
  'second_degree_av_block_mobitz1': 'ABNORMAL', 'lbbb': 'ABNORMAL', 'rbbb': 'ABNORMAL',
  'left_anterior_fascicular_block': 'ABNORMAL', 'left_posterior_fascicular_block': 'ABNORMAL',
  'nonspecific_ivcd': 'ABNORMAL', 'wpw_preexcitation': 'ABNORMAL', 'short_qt': 'ABNORMAL',
  'hypokalaemia_pattern': 'ABNORMAL', 'lvh': 'ABNORMAL', 'rvh': 'ABNORMAL', 'left_atrial_enlargement': 'ABNORMAL',
  'right_atrial_enlargement': 'ABNORMAL', 'low_voltage': 'ABNORMAL', 'pvcs': 'ABNORMAL', 'pacs': 'ABNORMAL',
  'left_axis_deviation': 'ABNORMAL', 'right_axis_deviation': 'ABNORMAL', 'extreme_axis_deviation': 'ABNORMAL',
  'lead_reversal_suspected': 'ABNORMAL', 'other': 'ABNORMAL',
};

const rhythmTiers = <String, String>{
  'ventricular_fibrillation': 'CRITICAL', 'ventricular_tachycardia': 'CRITICAL',
  'polymorphic_vt_torsades': 'CRITICAL', 'asystole': 'CRITICAL', 'idioventricular_rhythm': 'URGENT',
  'svt': 'URGENT', 'atrial_fibrillation': 'ABNORMAL', 'atrial_flutter': 'ABNORMAL',
  'junctional_rhythm': 'ABNORMAL', 'ectopic_atrial_rhythm': 'ABNORMAL', 'paced_rhythm': 'ABNORMAL',
  'sinus_tachycardia': 'ABNORMAL', 'other': 'ABNORMAL',
};

class Rule<T> {
  const Rule(this.id, this.tier, this.reason, this.when);
  final String id, tier, reason;
  final bool Function(T) when;
}

// ---- reading accessors (raw JSON, as produced by the engine or the old server) ----
num? _n(Object? v) => v is num ? v : null;
Json _m(Object? v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Json> _findings(Json r) => [for (final f in (r['findings'] as List? ?? const [])) _m(f)];
num? _rate(Json r) {
  final rb = _m(r['rate_bpm']);
  return (_n(rb['confidence']) ?? 0) >= otherMinConfidence ? _n(rb['value']) : null;
}

num _iv(Json r, String k) => _n(_m(r['intervals'])[k]) ?? 0;
bool _has(Json r, String code, [double min = otherMinConfidence]) =>
    _findings(r).any((f) => f['code'] == code && (_n(f['confidence']) ?? 0) >= min);
bool _rhythmIs(Json r, List<String> codes) {
  final rh = _m(r['rhythm']);
  return codes.contains(rh['code']) && (_n(rh['confidence']) ?? 0) >= otherMinConfidence;
}

final measurementRules = <Rule<Json>>[
  Rule('M1', 'CRITICAL', 'Severe bradycardia (rate below 40/min)', (r) {
    final v = _rate(r);
    return v != null && v < 40;
  }),
  Rule('M2', 'CRITICAL', 'Wide-complex tachycardia (rate 150/min or more with QRS 120 ms or more)', (r) {
    final v = _rate(r);
    return v != null && v >= 150 && _iv(r, 'qrs_ms') >= 120;
  }),
  Rule('M3', 'CRITICAL', 'Atrial fibrillation or flutter with pre-excitation (WPW)',
      (r) => _rhythmIs(r, ['atrial_fibrillation', 'atrial_flutter']) && _has(r, 'wpw_preexcitation', criticalMinConfidence)),
  Rule('M4', 'CRITICAL', 'Markedly prolonged QTc (500 ms or more)', (r) => _iv(r, 'qtc_ms') >= 500),
  Rule('M5', 'URGENT', 'Very fast rate (150/min or more)', (r) {
    final v = _rate(r);
    return v != null && v >= 150;
  }),
  Rule('M6', 'URGENT', 'Marked bradycardia (rate 40–49/min)', (r) {
    final v = _rate(r);
    return v != null && v >= 40 && v < 50;
  }),
  Rule('M7', 'URGENT', 'Atrial fibrillation or flutter with fast ventricular rate (120/min or more)', (r) {
    final v = _rate(r);
    return _rhythmIs(r, ['atrial_fibrillation', 'atrial_flutter']) && v != null && v >= 120;
  }),
  Rule('M8', 'ABNORMAL', 'Rate above 100/min', (r) {
    final v = _rate(r);
    return v != null && v > 100 && v < 150;
  }),
  Rule('M9', 'ABNORMAL', 'Rate 50–59/min', (r) {
    final v = _rate(r);
    return v != null && v >= 50 && v < 60;
  }),
  Rule('M10', 'ABNORMAL', 'Broad QRS (120 ms or more)', (r) => _iv(r, 'qrs_ms') >= 120),
  Rule('M11', 'ABNORMAL', 'Prolonged PR interval (more than 200 ms)', (r) => _iv(r, 'pr_ms') > 200),
  Rule('M12', 'URGENT', 'Prolonged QTc (470–499 ms)', (r) {
    final q = _iv(r, 'qtc_ms');
    return q >= 470 && q < 500;
  }),
];

class ContextInput {
  ContextInput(this.ctx, this.ecg, this.ecgTier);
  final Json ctx, ecg;
  final String ecgTier;
}

List _list(Json c, String k) => (c[k] as List?) ?? const [];
bool _chestPain(Json c) => _list(c, 'complaints').contains('chest_pain');
bool _hypotension(Json c) => _n(c['sbp']) != null && _n(c['sbp'])! < 90;
bool _stOrT(Json r) => _findings(r).any((f) =>
    ['st_elevation', 'st_depression', 't_wave'].contains(f['category']) &&
    (_n(f['confidence']) ?? 0) >= criticalMinConfidence);
const _conductionCodes = [
  'first_degree_av_block', 'second_degree_av_block_mobitz1', 'second_degree_av_block_mobitz2',
  'high_grade_av_block', 'third_degree_av_block', 'lbbb', 'rbbb', 'left_anterior_fascicular_block',
  'left_posterior_fascicular_block', 'nonspecific_ivcd', 'wpw_preexcitation', 'sinus_pause', 'long_qt',
  'brugada_type1',
];
bool _conduction(Json r) =>
    _findings(r).any((f) =>
        (f['category'] == 'conduction' || _conductionCodes.contains(f['code'])) &&
        (_n(f['confidence']) ?? 0) >= criticalMinConfidence) ||
    _iv(r, 'qrs_ms') >= 120 ||
    _iv(r, 'pr_ms') > 200 ||
    _iv(r, 'qtc_ms') >= 470;

final contextRules = <Rule<ContextInput>>[
  Rule('C1', 'CRITICAL', 'Hypotension (systolic below 90) with an abnormal ECG',
      (i) => _hypotension(i.ctx) && severity[i.ecgTier]! >= severity['ABNORMAL']!),
  Rule('C2', 'CRITICAL', 'Chest pain with hypotension (systolic below 90)', (i) => _chestPain(i.ctx) && _hypotension(i.ctx)),
  Rule('C3', 'URGENT', 'Hypotension (systolic below 90)', (i) => _hypotension(i.ctx)),
  Rule('C4', 'URGENT', 'Chest pain with ST/T changes', (i) => _chestPain(i.ctx) && _stOrT(i.ecg)),
  Rule('C5', 'URGENT', 'Syncope or near-syncope with a conduction abnormality',
      (i) => _list(i.ctx, 'complaints').contains('syncope') && _conduction(i.ecg)),
  Rule('C6', 'URGENT', 'Syncope or near-syncope with a rate below 50/min', (i) =>
      _list(i.ctx, 'complaints').contains('syncope') &&
      ((_n(_m(i.ecg['rate_bpm'])['value']) ?? 999) < 50 || (_n(i.ctx['heart_rate']) ?? 999) < 50)),
  Rule('C7', 'URGENT', 'Very high blood pressure (above 180/120)',
      (i) => (_n(i.ctx['sbp']) ?? 0) > 180 || (_n(i.ctx['dbp']) ?? 0) > 120),
  Rule('C8', 'CRITICAL', 'Severe hypoxia (SpO2 below 85%)', (i) => _n(i.ctx['spo2']) != null && _n(i.ctx['spo2'])! < 85),
  Rule('C9', 'URGENT', 'Low oxygen saturation (SpO2 below 90%)', (i) => _n(i.ctx['spo2']) != null && _n(i.ctx['spo2'])! < 90),
  Rule('C10', 'URGENT', 'Measured heart rate below 40 or above 150/min',
      (i) => _n(i.ctx['heart_rate']) != null && (_n(i.ctx['heart_rate'])! < 40 || _n(i.ctx['heart_rate'])! > 150)),
  Rule(
      'C11',
      'URGENT',
      'Chest pain in a higher-risk patient (age 40+, diabetes or known heart disease): '
          'a non-diagnostic ECG does not exclude ACS — repeat ECGs and troponin',
      (i) =>
          _chestPain(i.ctx) &&
          ((_n(i.ctx['age']) ?? 0) >= 40 ||
              _list(i.ctx, 'conditions').contains('diabetes') ||
              _list(i.ctx, 'conditions').contains('known_heart_disease'))),
  Rule('C12', 'URGENT', 'Palpitations or syncope with pre-excitation (WPW)', (i) =>
      (_list(i.ctx, 'complaints').contains('palpitations') || _list(i.ctx, 'complaints').contains('syncope')) &&
      _has(i.ecg, 'wpw_preexcitation', criticalMinConfidence)),
  Rule('C13', 'URGENT', 'Breathlessness with low voltage or electrical alternans (consider effusion/tamponade)', (i) =>
      _list(i.ctx, 'complaints').contains('breathlessness') &&
      (_has(i.ecg, 'low_voltage', criticalMinConfidence) || _has(i.ecg, 'electrical_alternans', criticalMinConfidence))),
  Rule('C14', 'URGENT', 'Kidney disease with T-wave or conduction changes (check potassium)', (i) =>
      _list(i.ctx, 'conditions').contains('ckd') &&
      (_findings(i.ecg).any((f) => f['category'] == 't_wave' && (_n(f['confidence']) ?? 0) >= criticalMinConfidence) ||
          _iv(i.ecg, 'qrs_ms') >= 120)),
];

// ---- engine ----
class Reason {
  Reason(this.rule, this.tier, this.text);
  final String rule, tier, text;
  Json toJson() => {'rule': rule, 'tier': tier, 'text': text};
}

class Evaluation {
  Evaluation(this.tier, this.reasons, {this.ecgTier, this.escalations = const []});
  final String tier;
  final List<Reason> reasons;
  final String? ecgTier;
  final List<Reason> escalations;
}

String maxTier(String a, String b) => severity[a]! >= severity[b]! ? a : b;

/// Stable sort by tier, highest first (JavaScript's Array.sort is stable; Dart's is not guaranteed).
List<Reason> _byTier(List<Reason> v) {
  final idx = List<int>.generate(v.length, (i) => i)
    ..sort((a, b) {
      final d = severity[v[b].tier]! - severity[v[a].tier]!;
      return d != 0 ? d : a - b;
    });
  return [for (final i in idx) v[i]];
}

Evaluation evaluateEcg(Json r) {
  final reasons = <Reason>[];
  for (final f in _findings(r)) {
    final tier = findingTiers[f['code']];
    if (tier == null) continue;
    final min = tier == 'CRITICAL' ? criticalMinConfidence : otherMinConfidence;
    if ((_n(f['confidence']) ?? 0) < min) continue;
    final leads = (f['leads'] as List? ?? const []);
    reasons.add(Reason('F:${f['code']}', tier, '${f['name']}${leads.isNotEmpty ? ' (${leads.join(', ')})' : ''}'));
  }
  final rh = _m(r['rhythm']);
  final rt = rhythmTiers[rh['code']];
  if (rt != null) {
    final min = rt == 'CRITICAL' ? criticalMinConfidence : otherMinConfidence;
    if ((_n(rh['confidence']) ?? 0) >= min) reasons.add(Reason('R:${rh['code']}', rt, 'Rhythm: ${rh['label']}'));
  }
  for (final m in measurementRules) {
    if (m.when(r)) reasons.add(Reason(m.id, m.tier, m.reason));
  }
  final seen = <String>{};
  final unique = [for (final x in _byTier(reasons)) if (seen.add(x.text)) x];
  final q = _m(r['image_quality']);
  final unreadable = q['readable'] != true || (_n(q['confidence']) ?? 0) < minImageConfidence;
  final hasCritical = unique.any((x) => x.tier == 'CRITICAL');
  if (unreadable && !hasCritical) {
    return Evaluation('UNREADABLE',
        [Reason('Q1', 'UNREADABLE', 'Image quality too low for a reliable reading — retake the photo')]);
  }
  var tier = 'NO_CRITICAL_PATTERN';
  for (final x in unique) {
    tier = maxTier(tier, x.tier);
  }
  if (unreadable && hasCritical) {
    unique.add(Reason('Q2', 'UNREADABLE',
        'Image quality is poor — critical pattern flagged anyway; confirm on the original ECG'));
  }
  return Evaluation(tier, unique);
}

/// Final tier with clinical context. Never lower than the ECG-only tier.
Evaluation evaluateWithContext(Json ecg, Json ctx) {
  final base = evaluateEcg(ecg);
  final input = ContextInput(ctx, ecg, base.tier);
  final esc = _byTier([for (final c in contextRules) if (c.when(input)) Reason(c.id, c.tier, c.reason)]);
  var tier = base.tier;
  for (final e in esc) {
    tier = maxTier(tier, e.tier);
  }
  return Evaluation(tier, base.reasons, ecgTier: base.tier, escalations: esc);
}
