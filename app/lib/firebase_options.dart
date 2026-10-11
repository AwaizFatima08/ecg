// PLACEHOLDER Firebase options for the local emulator ("demo-" project: no
// real Firebase resources, nothing leaves the LAN).
//
// When the real Firebase project exists, regenerate this file with:
//   flutterfire configure --project=<project-id> --platforms=android
// which overwrites it with the real options.
// ignore_for_file: type=lint
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      default:
        throw UnsupportedError('ECG Reader V1 supports Android only.');
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaDemoEmulatorOnlyKey0000000000000000', // format-valid dummy; emulator only
    appId: '1:123456789012:android:0123456789abcdef',
    messagingSenderId: '123456789012',
    projectId: 'demo-ecg-reader',
  );
}
