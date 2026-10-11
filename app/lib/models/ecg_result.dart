import 'alert_tier.dart';

/// Result of one ECG reading. Lives in memory only: it is never written to
/// disk and is discarded when the user leaves the result screen.
class EcgResult {
  EcgResult({
    required this.readingJson,
    required this.tier,
    required this.reasons,
    required this.model,
    required this.promptVersion,
    required this.rulesVersion,
  });

  /// The model's structured reading exactly as returned (sent back unchanged
  /// for the optional clinical-context reassessment; the image is not resent).
  final Map<String, dynamic> readingJson;
  final AlertTier tier;
  final List<AlertReason> reasons;
  final String model;
  final String promptVersion;
  final String rulesVersion;

  factory EcgResult.fromResponse(Map<String, dynamic> j) {
    final alert = _map(j['alert']);
    return EcgResult(
      readingJson: _map(j['reading']),
      tier: AlertTier.fromCode(alert['tier'] as String?),
      reasons: _maps(alert['reasons']).map(AlertReason.fromJson).toList(),
      model: j['model'] as String? ?? '',
      promptVersion: j['promptVersion'] as String? ?? '',
      rulesVersion: j['rulesVersion'] as String? ?? '',
    );
  }

  EcgReading get reading => EcgReading(readingJson);
}

class AlertReason {
  AlertReason(this.rule, this.tier, this.text);
  final String rule;
  final AlertTier tier;
  final String text;

  factory AlertReason.fromJson(Map<String, dynamic> j) =>
      AlertReason(j['rule'] as String? ?? '', AlertTier.fromCode(j['tier'] as String?), j['text'] as String? ?? '');
}

/// Result of reassessment with clinical context.
class ContextAssessment {
  ContextAssessment({required this.tier, required this.ecgTier, required this.escalations});
  final AlertTier tier;
  final AlertTier ecgTier;
  final List<AlertReason> escalations;

  factory ContextAssessment.fromResponse(Map<String, dynamic> j) => ContextAssessment(
        tier: AlertTier.fromCode(j['tier'] as String?),
        ecgTier: AlertTier.fromCode(j['ecgTier'] as String?),
        escalations: _maps(j['escalations']).map(AlertReason.fromJson).toList(),
      );
}

/// Read-only view over the reading JSON (schema: functions/src/schema/ecgResult.ts).
class EcgReading {
  EcgReading(this.j);
  final Map<String, dynamic> j;

  Map<String, dynamic> get _quality => _map(j['image_quality']);
  bool get readable => _quality['readable'] == true;
  double get qualityConfidence => (_num(_quality['confidence']) ?? 0).toDouble();
  List<String> get qualityIssues => _list(_quality['issues']).cast<String>();

  Map<String, dynamic> get _cal => _map(j['calibration']);
  bool get calibrationAssumed => _cal['assumed'] == true;
  num? get paperSpeed => _num(_cal['paper_speed_mm_s']);
  num? get gain => _num(_cal['gain_mm_mv']);

  String get layout => j['layout'] as String? ?? '';
  num? get rate => _num(_map(j['rate_bpm'])['value']);
  double get rateConfidence => (_num(_map(j['rate_bpm'])['confidence']) ?? 0).toDouble();

  Map<String, dynamic> get _rhythm => _map(j['rhythm']);
  String get rhythmLabel => _rhythm['label'] as String? ?? '';
  String get rhythmCode => _rhythm['code'] as String? ?? '';
  bool? get regular => _rhythm['regular'] as bool?;
  double get rhythmConfidence => (_num(_rhythm['confidence']) ?? 0).toDouble();

  Map<String, dynamic> get _iv => _map(j['intervals']);
  num? get pr => _num(_iv['pr_ms']);
  num? get qrs => _num(_iv['qrs_ms']);
  num? get qt => _num(_iv['qt_ms']);
  num? get qtc => _num(_iv['qtc_ms']);

  String get axis => _map(j['axis'])['label'] as String? ?? '';
  double get axisConfidence => (_num(_map(j['axis'])['confidence']) ?? 0).toDouble();

  List<Finding> get findings => _maps(j['findings']).map(Finding.new).toList()
    ..sort((a, b) => b.confidence.compareTo(a.confidence));

  String get notes => j['model_notes'] as String? ?? '';
}

class Finding {
  Finding(this.j);
  final Map<String, dynamic> j;
  String get name => j['name'] as String? ?? '';
  String get code => j['code'] as String? ?? '';
  String get category => j['category'] as String? ?? '';
  List<String> get leads => _list(j['leads']).cast<String>();
  double get confidence => (_num(j['confidence']) ?? 0).toDouble();
}

Map<String, dynamic> _map(Object? o) => o is Map ? Map<String, dynamic>.from(o) : <String, dynamic>{};
List<dynamic> _list(Object? o) =>
    o is List ? o.map((e) => e is Map ? Map<String, dynamic>.from(e) : e).toList() : const [];
List<Map<String, dynamic>> _maps(Object? o) => _list(o).whereType<Map<String, dynamic>>().toList();
num? _num(Object? o) => o is num ? o : null;
