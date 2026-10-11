import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/env.dart';
import '../core/theme.dart';
import '../services/app_config.dart';
import 'disclaimer_screen.dart';

/// About / Disclaimer / Privacy (design-v1 screen 8).
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final cfg = AppConfig.instance;
    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(Copy.appName, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
            Text('Version ${cfg.version} (${cfg.build}) · HomiLabs', style: t.textTheme.bodySmall),
            const SizedBox(height: 16),
            const Text(
              'ECG Reader helps qualified clinicians read photographs of printed ECGs. An AI model describes '
              'the trace; a fixed, clinician-reviewed rule table then sets the alert level. It is decision support only.',
            ),
            const SizedBox(height: 20),
            Text('Privacy — nothing is saved', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text(
              '• No account and no login.\n'
              '• The ECG image is cropped and stripped of photo metadata (location, device, time) on your phone.\n'
              '• It is sent over an encrypted connection to our server, which passes it to an AI service '
              '(Anthropic) for reading. Our server does not store or log the image or the result.\n'
              '• The result and any clinical details you enter exist only on this screen and are discarded when you leave it.\n'
              '• The app keeps an anonymous, random ID only to limit how many readings can be made per day. '
              'It contains no ECG, result or patient data.\n'
              '• No analytics or advertising.',
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              style: TextButton.styleFrom(alignment: Alignment.centerLeft),
              onPressed: () => launchUrl(Uri.parse(Env.privacyUrl), mode: LaunchMode.externalApplication),
              icon: const Icon(Icons.open_in_new),
              label: const Text('Full privacy policy'),
            ),
            const Divider(height: 32),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.gavel_outlined),
              title: const Text('Disclaimer'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const DisclaimerScreen(readOnly: true)),
              ),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.article_outlined),
              title: const Text('Open-source licences'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => showLicensePage(context: context, applicationName: Copy.appName),
            ),
          ],
        ),
      ),
    );
  }
}
