import 'package:flutter/material.dart';

import '../models/ecg_result.dart';

/// One finding with leads and the model's confidence.
class FindingTile extends StatelessWidget {
  const FindingTile(this.finding, {super.key});
  final Finding finding;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final pctText = '${(finding.confidence * 100).round()}%';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(finding.name, style: t.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
              if (finding.leads.isNotEmpty)
                Text('Leads: ${finding.leads.join(', ')}', style: t.textTheme.bodySmall),
            ]),
          ),
          const SizedBox(width: 8),
          ConfidenceChip(finding.confidence, label: pctText),
        ],
      ),
    );
  }
}

class ConfidenceChip extends StatelessWidget {
  const ConfidenceChip(this.confidence, {super.key, required this.label});
  final double confidence;
  final String label;

  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    final low = confidence < 0.5;
    return Tooltip(
      message: 'Model confidence that this is visible on the image',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: low ? s.surfaceContainerHighest : s.secondaryContainer,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(low ? '$label · low' : label, style: Theme.of(context).textTheme.labelMedium),
      ),
    );
  }
}
