import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/clinical_context.dart';
import '../models/ecg_result.dart';
import '../services/ecg_api.dart';

/// Optional clinical context (design-v1 Section 7.3, screen 7).
/// Context can only RAISE the alert level. Nothing entered here is stored.
class ContextScreen extends StatefulWidget {
  const ContextScreen({super.key, required this.result, required this.initial});
  final EcgResult result;

  /// Edited in place, so values are still there if the doctor opens the form again.
  final ClinicalContext initial;
  @override
  State<ContextScreen> createState() => _ContextScreenState();
}

class _ContextScreenState extends State<ContextScreen> {
  final _form = GlobalKey<FormState>();
  late final ClinicalContext _ctx = widget.initial;
  bool _busy = false;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    _form.currentState!.save();
    setState(() => _busy = true);
    try {
      final a = await EcgApi.instance.reassess(widget.result, _ctx);
      if (mounted) Navigator.of(context).pop(a);
    } on EcgApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String? _range(String? v, int min, int max) {
    if (v == null || v.isEmpty) return null;
    final n = int.tryParse(v);
    if (n == null || n < min || n > max) return '$min–$max';
    return null;
  }

  Widget _num(String label, String suffix, int min, int max, int? initial, void Function(int?) save) => Expanded(
        child: TextFormField(
          initialValue: initial?.toString(),
          decoration: InputDecoration(labelText: label, suffixText: suffix),
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(3)],
          validator: (v) => _range(v, min, max),
          onSaved: (v) => save(v == null || v.isEmpty ? null : int.parse(v)),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Clinical context')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('All fields are optional. These details can only raise the alert level, never lower it.',
                  style: t.textTheme.bodyMedium),
              const SizedBox(height: 16),
              Row(children: [
                _num('Age', 'yrs', 0, 120, _ctx.age, (v) => _ctx.age = v),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    decoration: const InputDecoration(labelText: 'Sex'),
                    initialValue: _ctx.sex,
                    items: const [
                      DropdownMenuItem(value: 'male', child: Text('Male')),
                      DropdownMenuItem(value: 'female', child: Text('Female')),
                      DropdownMenuItem(value: 'other', child: Text('Other')),
                    ],
                    onChanged: (v) => _ctx.sex = v,
                  ),
                ),
              ]),
              const SizedBox(height: 20),
              Text('Presenting complaint', style: t.textTheme.titleSmall),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 4, children: [
                for (final e in ClinicalContext.complaintOptions.entries)
                  FilterChip(
                    label: Text(e.value),
                    selected: _ctx.complaints.contains(e.key),
                    onSelected: (s) => setState(() => s ? _ctx.complaints.add(e.key) : _ctx.complaints.remove(e.key)),
                  ),
              ]),
              if (_ctx.complaints.contains('chest_pain'))
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Chest pain ongoing now'),
                  value: _ctx.chestPainOngoing ?? false,
                  onChanged: (v) => setState(() => _ctx.chestPainOngoing = v),
                ),
              if (_ctx.complaints.contains('other'))
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: TextFormField(
                    decoration: const InputDecoration(labelText: 'Other complaint (no patient identifiers)'),
                    initialValue: _ctx.complaintOther,
                    maxLength: 200,
                    onSaved: (v) => _ctx.complaintOther = v,
                  ),
                ),
              const SizedBox(height: 16),
              Text('Vitals', style: t.textTheme.titleSmall),
              const SizedBox(height: 8),
              Row(children: [
                _num('Systolic', 'mmHg', 30, 300, _ctx.sbp, (v) => _ctx.sbp = v),
                const SizedBox(width: 12),
                _num('Diastolic', 'mmHg', 10, 200, _ctx.dbp, (v) => _ctx.dbp = v),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                _num('Heart rate', '/min', 10, 300, _ctx.heartRate, (v) => _ctx.heartRate = v),
                const SizedBox(width: 12),
                _num('SpO₂', '%', 40, 100, _ctx.spo2, (v) => _ctx.spo2 = v),
              ]),
              const SizedBox(height: 20),
              Text('Known conditions', style: t.textTheme.titleSmall),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 4, children: [
                for (final e in ClinicalContext.conditionOptions.entries)
                  FilterChip(
                    label: Text(e.value),
                    selected: _ctx.conditions.contains(e.key),
                    onSelected: (s) => setState(() => s ? _ctx.conditions.add(e.key) : _ctx.conditions.remove(e.key)),
                  ),
              ]),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 3))
                    : const Text('Update alert level'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
