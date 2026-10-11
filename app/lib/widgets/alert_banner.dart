import 'package:flutter/material.dart';

import '../models/alert_tier.dart';

/// Full-width alert banner at the top of the result (design-v1 Section 7.1).
class AlertBanner extends StatelessWidget {
  const AlertBanner({super.key, required this.tier, this.escalatedFrom});

  final AlertTier tier;

  /// Set when clinical context raised the tier.
  final AlertTier? escalatedFrom;

  @override
  Widget build(BuildContext context) {
    final fg = tier.foreground;
    return Semantics(
      liveRegion: true,
      label: 'Alert level ${tier.title}. ${tier.meaning}',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
        decoration: BoxDecoration(color: tier.background, borderRadius: BorderRadius.circular(16)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(tier.icon, color: fg, size: 30),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  tier.title,
                  style: TextStyle(color: fg, fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 0.3),
                ),
              ),
            ]),
            const SizedBox(height: 6),
            Text(tier.meaning, style: TextStyle(color: fg, fontSize: 15, height: 1.3)),
            if (escalatedFrom != null && escalatedFrom != tier) ...[
              const SizedBox(height: 8),
              Text(
                'Raised from ${escalatedFrom!.title} by the clinical details you entered.',
                style: TextStyle(color: fg, fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Small coloured dot + text used for each reason line.
class TierDot extends StatelessWidget {
  const TierDot(this.tier, {super.key});
  final AlertTier tier;

  @override
  Widget build(BuildContext context) => Container(
        width: 12,
        height: 12,
        margin: const EdgeInsets.only(top: 4),
        decoration: BoxDecoration(color: tier.background, shape: BoxShape.circle),
      );
}
