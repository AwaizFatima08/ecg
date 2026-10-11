import 'package:flutter/material.dart';

/// Alert tiers (design-v1 Section 7.1). There is deliberately no "Normal".
enum AlertTier {
  critical('CRITICAL', 'CRITICAL', 'Pattern consistent with immediate life threat — act now'),
  urgent('URGENT', 'URGENT', 'Significant abnormality needing prompt review'),
  abnormal('ABNORMAL', 'ABNORMAL', 'Abnormal, not time-critical on this image alone'),
  noCriticalPattern(
    'NO_CRITICAL_PATTERN',
    'NO CRITICAL PATTERN SEEN',
    'Nothing alarming detected on this image. This is not a statement that the ECG is normal.',
  ),
  unreadable('UNREADABLE', 'UNREADABLE / LOW QUALITY', 'The image cannot be interpreted reliably');

  const AlertTier(this.code, this.title, this.meaning);

  final String code;
  final String title;
  final String meaning;

  static AlertTier fromCode(String? code) =>
      AlertTier.values.firstWhere((t) => t.code == code, orElse: () => AlertTier.unreadable);

  /// Severity order matches the rules engine (functions/src/rules/alertRules.ts).
  int get severity => switch (this) {
        AlertTier.noCriticalPattern => 0,
        AlertTier.unreadable => 1,
        AlertTier.abnormal => 2,
        AlertTier.urgent => 3,
        AlertTier.critical => 4,
      };

  Color get background => switch (this) {
        AlertTier.critical => const Color(0xFFC62828),
        AlertTier.urgent => const Color(0xFFEF6C00),
        AlertTier.abnormal => const Color(0xFFF9A825),
        AlertTier.noCriticalPattern => const Color(0xFF546E7A),
        AlertTier.unreadable => const Color(0xFF757575),
      };

  Color get foreground => this == AlertTier.abnormal ? Colors.black : Colors.white;

  IconData get icon => switch (this) {
        AlertTier.critical => Icons.error,
        AlertTier.urgent => Icons.warning_amber_rounded,
        AlertTier.abnormal => Icons.info,
        AlertTier.noCriticalPattern => Icons.remove_circle_outline,
        AlertTier.unreadable => Icons.hide_image_outlined,
      };
}
