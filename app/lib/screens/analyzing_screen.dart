import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../engine/engine.dart';
import 'result_screen.dart';

/// Reads the ECG on the phone (design-v1 screen 5). Nothing is sent anywhere;
/// the image bytes exist only in this screen's memory.
class AnalyzingScreen extends StatefulWidget {
  const AnalyzingScreen({super.key, required this.jpeg});
  final Uint8List jpeg;
  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  String? _error;
  String _step = 'Starting…';
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
      final result = await EcgEngine.instance.interpret(widget.jpeg, onStep: (s) {
        if (mounted && attempt == _attempt) setState(() => _step = s);
      });
      if (!mounted || _cancelled || attempt != _attempt) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ResultScreen(result: result)));
    } on EngineException catch (e) {
      if (mounted && !_cancelled && attempt == _attempt) setState(() => _error = e.message);
    } catch (e, st) {
      debugPrint('interpret failed: $e\n$st');
      if (mounted && !_cancelled && attempt == _attempt) {
        setState(() => _error = 'Reading failed on this image. Please retake the photo and try again.');
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
                    Text(_step, style: t.textTheme.titleLarge, textAlign: TextAlign.center),
                    const SizedBox(height: 8),
                    Text('Read on this phone — nothing is uploaded.', style: t.textTheme.bodyMedium),
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
                    Icon(Icons.error_outline, size: 56, color: t.colorScheme.error),
                    const SizedBox(height: 16),
                    Text(e, textAlign: TextAlign.center, style: t.textTheme.titleMedium),
                    const SizedBox(height: 24),
                    FilledButton(onPressed: _run, child: const Text('Try again')),
                    const SizedBox(height: 10),
                    OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Back')),
                  ]),
          ),
        ),
      ),
    );
  }
}
