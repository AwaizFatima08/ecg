import 'package:flutter/material.dart';

import '../services/image_prep.dart';
import 'analyzing_screen.dart';

/// Preview of exactly what will be sent, with quality warnings and the
/// patient-details reminder (design-v1 screen 4, risk 3.5).
class ConfirmScreen extends StatelessWidget {
  const ConfirmScreen({super.key, required this.image});
  final PreparedImage image;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Check the image')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: InteractiveViewer(maxScale: 5, child: Image.memory(image.jpeg, gaplessPlayback: true)),
            ),
            const SizedBox(height: 4),
            Text('${image.width} × ${image.height} px · pinch to zoom', style: t.textTheme.bodySmall, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Card(
              color: t.colorScheme.tertiaryContainer,
              child: const ListTile(
                leading: Icon(Icons.badge_outlined),
                title: Text('No patient details?'),
                subtitle: Text('Make sure no name, ID number or other identifying text is visible. '
                    'If it is, go back and crop it out.'),
              ),
            ),
            for (final w in image.warnings)
              Card(
                color: t.colorScheme.errorContainer,
                child: ListTile(leading: const Icon(Icons.warning_amber_rounded), title: Text(w.message)),
              ),
            const SizedBox(height: 12),
            FilledButton.icon(
              icon: const Icon(Icons.monitor_heart_outlined),
              label: Text(image.warnings.isEmpty ? 'Read this ECG' : 'Read anyway'),
              onPressed: () => Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => AnalyzingScreen(jpeg: image.jpeg)),
              ),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              icon: const Icon(Icons.replay),
              label: const Text('Retake or choose another'),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
      ),
    );
  }
}
