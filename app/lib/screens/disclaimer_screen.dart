import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../services/app_config.dart';
import 'home_screen.dart';

/// First-run disclaimer; must be accepted. Versioned via Remote Config, so a
/// changed disclaimer is shown again (design-v1 Section 9, screen 1).
class DisclaimerScreen extends StatefulWidget {
  const DisclaimerScreen({super.key, this.readOnly = false});

  /// Opened from About: show the text without the accept step.
  final bool readOnly;

  @override
  State<DisclaimerScreen> createState() => _DisclaimerScreenState();
}

class _DisclaimerScreenState extends State<DisclaimerScreen> {
  bool _clinician = false;
  bool _understood = false;

  Future<void> _accept() async {
    await AppConfig.instance.acceptDisclaimer();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Before you start'), automaticallyImplyLeading: widget.readOnly),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(Copy.appName, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text('Clinical decision support for reading paper ECGs', style: t.textTheme.bodyLarge),
            const SizedBox(height: 20),
            for (final p in Copy.disclaimerPoints)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Padding(padding: EdgeInsets.only(top: 2), child: Icon(Icons.check_circle_outline, size: 20)),
                  const SizedBox(width: 10),
                  Expanded(child: Text(p, style: t.textTheme.bodyLarge?.copyWith(height: 1.35))),
                ]),
              ),
            if (!widget.readOnly) ...[
              const Divider(height: 32),
              CheckboxListTile(
                value: _clinician,
                onChanged: (v) => setState(() => _clinician = v ?? false),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text('I am a qualified doctor or clinician'),
              ),
              CheckboxListTile(
                value: _understood,
                onChanged: (v) => setState(() => _understood = v ?? false),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text('I understand this is decision support only and my own reading prevails'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _clinician && _understood ? _accept : null,
                child: const Text('Accept and continue'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
