import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../services/ecg_api.dart';
import 'result_screen.dart';

/// Sends the image and waits, with retry and clear failure messages
/// (design-v1 screen 5). The image bytes exist only in this screen's memory.
class AnalyzingScreen extends StatefulWidget {
  const AnalyzingScreen({super.key, required this.jpeg});
  final Uint8List jpeg;
  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  EcgApiException? _error;
  bool _cancelled = false;
  int _attempt = 0;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    final attempt = ++_attempt;
    if (_error != null) setState(() => _error = null); // not on the first run (called from initState)
    try {
      final result = await EcgApi.instance.interpret(widget.jpeg);
      if (!mounted || _cancelled || attempt != _attempt) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ResultScreen(result: result)));
    } on EcgApiException catch (e) {
      if (mounted && !_cancelled && attempt == _attempt) setState(() => _error = e);
    } catch (e, st) {
      debugPrint('interpret failed: $e\n$st');
      if (mounted && !_cancelled && attempt == _attempt) {
        setState(() => _error = EcgApiException('Reading failed. Please try again.'));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final e = _error;
    return PopScope(
      onPopInvokedWithResult: (didPop, _) => _cancelled = true,
      child: Scaffold(
        appBar: AppBar(title: const Text('Reading ECG')),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: e == null
                ? Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const SizedBox(width: 56, height: 56, child: CircularProgressIndicator(strokeWidth: 5)),
                    const SizedBox(height: 24),
                    Text('Reading the ECG…', style: t.textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text('This usually takes 20–60 seconds.', style: t.textTheme.bodyMedium),
                    const SizedBox(height: 32),
                    TextButton(
                      onPressed: () {
                        _cancelled = true;
                        Navigator.of(context).pop();
                      },
                      child: const Text('Cancel'),
                    ),
                  ])
                : Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Icon(Icons.cloud_off, size: 56, color: t.colorScheme.error),
                    const SizedBox(height: 16),
                    Text(e.message, textAlign: TextAlign.center, style: t.textTheme.titleMedium),
                    const SizedBox(height: 24),
                    if (e.retryable) FilledButton(onPressed: _run, child: const Text('Try again')),
                    const SizedBox(height: 10),
                    OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Back')),
                  ]),
          ),
        ),
      ),
    );
  }
}
