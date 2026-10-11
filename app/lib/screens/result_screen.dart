import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../models/alert_tier.dart';
import '../models/clinical_context.dart';
import '../models/ecg_result.dart';
import '../widgets/alert_banner.dart';
import '../widgets/finding_tile.dart';
import 'context_screen.dart';

/// Result (design-v1 screen 6). The result lives only in this screen's state:
/// leaving the screen discards it. Nothing is saved.
class ResultScreen extends StatefulWidget {
  const ResultScreen({super.key, required this.result});
  final EcgResult result;
  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  ContextAssessment? _ctx;
  ClinicalContext? _ctxInput; // kept so the form can be edited again

  AlertTier get _tier => _ctx?.tier ?? widget.result.tier;

  Future<void> _addContext() async {
    final input = _ctxInput ?? ClinicalContext();
    final a = await Navigator.of(context).push<ContextAssessment>(
      MaterialPageRoute(builder: (_) => ContextScreen(result: widget.result, initial: input)),
    );
    if (a != null && mounted) {
      setState(() {
        _ctx = a;
        _ctxInput = input;
      });
    }
  }

  Future<bool> _confirmLeave() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Leave this result?'),
        content: const Text('Nothing is saved. The result will be discarded.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Stay')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Leave')),
        ],
      ),
    );
    return ok ?? false;
  }

  Future<void> _newEcg() async {
    if (await _confirmLeave() && mounted) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    final rd = r.reading;
    final t = Theme.of(context);
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _confirmLeave() && context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Result')),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (r.model.startsWith('mock'))
                Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(10),
                  color: Colors.purple,
                  child: const Text('TEST MODE — mock reading, not an interpretation of this image',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800), textAlign: TextAlign.center),
                ),
              AlertBanner(tier: _tier, escalatedFrom: _ctx != null ? r.tier : null),
              const SizedBox(height: 8),
              Text(Copy.decisionSupport,
                  style: t.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600), textAlign: TextAlign.center),
              const SizedBox(height: 12),
              if (_ctx != null && _ctx!.escalations.isNotEmpty)
                _Section(
                  title: 'From the clinical details',
                  children: [for (final e in _ctx!.escalations) _ReasonLine(e)],
                ),
              if (_ctx != null && _ctx!.escalations.isEmpty)
                const _Section(
                  title: 'From the clinical details',
                  children: [Text('The clinical details did not raise the alert level.')],
                ),
              _Section(
                title: _ctx == null ? 'Why this alert level' : 'From the ECG',
                children: r.reasons.isEmpty
                    ? [const Text('No rule in the alert table matched this reading.')]
                    : [for (final x in r.reasons) _ReasonLine(x)],
              ),
              _Section(title: 'Measurements', children: [
                _kv('Rate', rd.rate == null ? 'cannot assess' : '${rd.rate} /min', rd.rateConfidence),
                _kv('Rhythm', '${rd.rhythmLabel}${rd.regular == null ? '' : rd.regular! ? ', regular' : ', irregular'}',
                    rd.rhythmConfidence),
                _kv('PR', _ms(rd.pr)),
                _kv('QRS', _ms(rd.qrs)),
                _kv('QT / QTc', '${_ms(rd.qt)} / ${_ms(rd.qtc)}'),
                _kv('Axis', rd.axis.replaceAll('_', ' '), rd.axisConfidence),
              ]),
              _Section(
                title: 'Findings',
                children: rd.findings.isEmpty
                    ? [const Text('No specific findings listed.')]
                    : [for (final f in rd.findings) FindingTile(f)],
              ),
              _Section(title: 'Image quality and limits', children: [
                Text(
                  '${rd.readable ? 'Readable' : 'Not reliably readable'} · quality ${(rd.qualityConfidence * 100).round()}%'
                  '${rd.qualityIssues.isEmpty ? '' : ' · ${rd.qualityIssues.map((s) => s.replaceAll('_', ' ')).join(', ')}'}',
                ),
                const SizedBox(height: 4),
                Text(rd.calibrationAssumed
                    ? 'Calibration not visible: 25 mm/s and 10 mm/mV assumed.'
                    : 'Calibration: ${rd.paperSpeed ?? '?'} mm/s, ${rd.gain ?? '?'} mm/mV.'),
                if (rd.notes.isNotEmpty) ...[const SizedBox(height: 4), Text(rd.notes, style: t.textTheme.bodySmall)],
                const SizedBox(height: 6),
                Text(
                  'A single ECG image can miss intermittent or evolving changes. Compare with old ECGs and repeat if the picture changes.',
                  style: t.textTheme.bodySmall,
                ),
              ]),
              const SizedBox(height: 8),
              if (_tier == AlertTier.unreadable)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text('Tip: retake flat, in even light, with the trace filling the frame.',
                      style: t.textTheme.bodyMedium, textAlign: TextAlign.center),
                ),
              FilledButton.icon(
                onPressed: _addContext,
                icon: const Icon(Icons.assignment_outlined),
                label: Text(_ctx == null ? 'Add clinical context (optional)' : 'Edit clinical context'),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(onPressed: _newEcg, icon: const Icon(Icons.add_a_photo_outlined), label: const Text('New ECG')),
              const SizedBox(height: 16),
              Text('Reading: ${r.model} · prompt ${r.promptVersion} · rules ${r.rulesVersion}',
                  style: t.textTheme.labelSmall, textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }

  static String _ms(num? v) => v == null ? '—' : '${v.round()} ms';

  Widget _kv(String k, String v, [double? confidence]) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          SizedBox(width: 90, child: Text(k, style: const TextStyle(fontWeight: FontWeight.w600))),
          Expanded(child: Text(v)),
          if (confidence != null) ConfidenceChip(confidence, label: '${(confidence * 100).round()}%'),
        ]),
      );
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: 10),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            ...children,
          ]),
        ),
      );
}

class _ReasonLine extends StatelessWidget {
  const _ReasonLine(this.reason);
  final AlertReason reason;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          TierDot(reason.tier),
          const SizedBox(width: 10),
          Expanded(child: Text(reason.text)),
        ]),
      );
}
