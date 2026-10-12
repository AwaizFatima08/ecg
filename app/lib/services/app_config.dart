import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_remote_config/firebase_remote_config.dart';
import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/env.dart';
import '../firebase_options.dart';
import '../firebase_options_demo.dart';

/// Start-up, Remote Config (kill switch, minimum version, disclaimer version)
/// and the only thing the app stores locally: which disclaimer version the
/// doctor accepted. No ECG data is ever stored.
class AppConfig {
  AppConfig._();
  static final instance = AppConfig._();

  static const _kAccepted = 'accepted_disclaimer_version';

  bool enabled = true;
  String disabledMessage = 'ECG reading is temporarily unavailable. Please try again later.';
  int minBuild = 0;
  int disclaimerVersion = 1;
  int acceptedDisclaimer = 0;
  int build = 0;
  String version = '';

  bool get updateRequired => build < minBuild;
  bool get disclaimerAccepted => acceptedDisclaimer >= disclaimerVersion;

  Future<void> init() async {
    // The emulator runs as the offline "demo-" project; everything else uses the real project.
    await Firebase.initializeApp(
      options: Env.useEmulator ? DemoFirebaseOptions.currentPlatform : DefaultFirebaseOptions.currentPlatform,
    );

    if (Env.useEmulator) {
      FirebaseFunctions.instanceFor(region: Env.functionsRegion).useFunctionsEmulator(Env.emulatorHost, 5001);
      await FirebaseAuth.instance.useAuthEmulator(Env.emulatorHost, 9099);
    } else {
      // Play Integrity in release; the debug provider (token registered in the
      // Firebase console) for debug builds on test phones.
      await FirebaseAppCheck.instance.activate(
        providerAndroid: kReleaseMode ? const AndroidPlayIntegrityProvider() : const AndroidDebugProvider(),
      );
    }

    final info = await PackageInfo.fromPlatform();
    build = int.tryParse(info.buildNumber) ?? 0;
    version = info.version;

    final prefs = await SharedPreferences.getInstance();
    acceptedDisclaimer = prefs.getInt(_kAccepted) ?? 0;

    if (!Env.useEmulator) await _loadRemoteConfig();
  }

  Future<void> _loadRemoteConfig() async {
    final rc = FirebaseRemoteConfig.instance;
    try {
      await rc.setConfigSettings(RemoteConfigSettings(
        fetchTimeout: const Duration(seconds: 8),
        minimumFetchInterval: kReleaseMode ? const Duration(minutes: 30) : Duration.zero,
      ));
      await rc.setDefaults({
        'ecg_enabled': true,
        'ecg_disabled_message': disabledMessage,
        'min_build': 0,
        'disclaimer_version': 1,
      });
      await rc.fetchAndActivate();
    } catch (_) {
      // Offline or Remote Config unreachable: defaults / last values apply.
    }
    enabled = rc.getBool('ecg_enabled');
    disabledMessage = rc.getString('ecg_disabled_message').isEmpty ? disabledMessage : rc.getString('ecg_disabled_message');
    minBuild = rc.getInt('min_build');
    disclaimerVersion = rc.getInt('disclaimer_version').clamp(1, 1000);
  }

  Future<void> acceptDisclaimer() async {
    acceptedDisclaimer = disclaimerVersion;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kAccepted, disclaimerVersion);
  }
}
