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
              'ECG Reader helps qualified clinicians read photographs of printed ECGs. The reading engine runs '
              'entirely on this phone: it traces the ECG from the photo, measures it, and a fixed, '
              'clinician-reviewed rule table sets the alert level. It is decision support only.',
            ),
            const SizedBox(height: 20),
            Text('Privacy — nothing leaves your phone', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text(
              '• No account and no login.\n'
              '• The ECG photo is read on this phone. It is never uploaded to any server or AI service.\n'
              '• The result and any clinical details you enter exist only on the result screen and are discarded '
              'when you leave it. No history, no gallery copy, no temporary files.\n'
              '• The app only goes online to check for safety notices and required updates.\n'
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
            const SizedBox(height: 8),
            Text('Credits', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text(
              '• ECG tracing model: Open-ECG-Digitizer, Stenhede E., Bjørnstad A.M., Ranjbar A., '
              '"Digitizing Paper ECGs at Scale: An Open-Source Algorithm for Clinical Research", '
              'npj Digital Medicine (2026). Weights adapted (int8) under CC BY-SA 4.0.\n'
              '• Training and test data: PTB-XL (Wagner P. et al., Scientific Data 2020, PhysioNet, CC BY 4.0); '
              'ecg-arrhythmia — Chapman-Shaoxing and Ningbo (Zheng J. et al., PhysioNet, CC BY 4.0); '
              'ACS 12-lead ECG dataset (Du et al., Scientific Data 2026, figshare, CC0); '
              'Shandong Provincial Hospital database (Liu H. et al., Scientific Data 2022, figshare, CC0); '
              'MIT-BIH Malignant Ventricular Ectopy and CU Ventricular Tachyarrhythmia databases (PhysioNet, ODC-By 1.0); '
              'ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0) — test only.\n'
              '• Not detected by this version: hyperkalaemia, Brugada and torsades patterns, posterior and right-ventricular infarction, '
              'pericarditis, Wellens and de Winter patterns, paediatric ECGs. Supported: a photo or scan of an original standard 12-lead print (25 mm/s, 10 s across; 3×4 with or without a lead II rhythm strip, 3×4 with three strips, or 12 stacked leads). Reduced or re-sized copies, such as textbook pages or thumbnails, are refused because their scale cannot be checked.',
              style: TextStyle(fontSize: 13),
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
