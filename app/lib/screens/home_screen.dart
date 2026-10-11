import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/theme.dart';
import '../services/app_config.dart';
import 'about_screen.dart';
import 'capture_screen.dart';
import 'crop_flow.dart';

/// Two big buttons: Scan ECG and Choose from gallery (design-v1 screen 2).
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _busy = false;

  Future<void> _scan() async {
    final path = await Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => const CaptureScreen()));
    if (path != null && mounted) await CropFlow.start(context, path);
  }

  Future<void> _gallery() async {
    setState(() => _busy = true);
    try {
      // Android photo picker: no storage permission needed.
      final x = await ImagePicker().pickImage(source: ImageSource.gallery, requestFullMetadata: false);
      if (x != null && mounted) await CropFlow.start(context, x.path);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cfg = AppConfig.instance;
    final t = Theme.of(context);
    final blocked = !cfg.enabled || cfg.updateRequired;
    return Scaffold(
      appBar: AppBar(
        title: const Text(Copy.appName),
        actions: [
          IconButton(
            tooltip: 'About, disclaimer and privacy',
            icon: const Icon(Icons.info_outline),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AboutScreen())),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (!cfg.enabled) _Notice(icon: Icons.pause_circle_outline, text: cfg.disabledMessage),
              if (cfg.enabled && cfg.updateRequired)
                const _Notice(
                  icon: Icons.system_update,
                  text: 'A newer version of ECG Reader is required. Please update the app from Google Play.',
                ),
              const Spacer(),
              Icon(Icons.monitor_heart_outlined, size: 72, color: t.colorScheme.primary),
              const SizedBox(height: 12),
              Text('Read a printed ECG', textAlign: TextAlign.center, style: t.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(
                'Photograph a 12-lead ECG or rhythm strip lying flat in even light, '
                'then crop to the trace so the patient\'s details are left out.',
                textAlign: TextAlign.center,
                style: t.textTheme.bodyMedium,
              ),
              const Spacer(),
              FilledButton.icon(
                onPressed: blocked || _busy ? null : _scan,
                icon: const Icon(Icons.photo_camera_outlined),
                label: const Text('Scan ECG'),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: blocked || _busy ? null : _gallery,
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Choose from gallery'),
              ),
              const SizedBox(height: 16),
              Text(Copy.decisionSupport, textAlign: TextAlign.center, style: t.textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Card(
        color: Theme.of(context).colorScheme.errorContainer,
        child: ListTile(leading: Icon(icon), title: Text(text)),
      );
}
