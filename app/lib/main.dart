import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/theme.dart';
import 'screens/disclaimer_screen.dart';
import 'screens/home_screen.dart';
import 'services/app_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  Object? startupError;
  try {
    await AppConfig.instance.init();
  } catch (e) {
    startupError = e;
  }
  runApp(EcgReaderApp(startupError: startupError));
}

class EcgReaderApp extends StatelessWidget {
  const EcgReaderApp({super.key, this.startupError});
  final Object? startupError;

  @override
  Widget build(BuildContext context) {
    final cfg = AppConfig.instance;
    return MaterialApp(
      title: Copy.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      home: startupError != null
          ? const _StartupFailed()
          : (cfg.disclaimerAccepted ? const HomeScreen() : const DisclaimerScreen()),
    );
  }
}

class _StartupFailed extends StatelessWidget {
  const _StartupFailed();
  @override
  Widget build(BuildContext context) => const Scaffold(
        body: Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text('The app could not start. Please check your internet connection and reopen it.',
                textAlign: TextAlign.center),
          ),
        ),
      );
}
