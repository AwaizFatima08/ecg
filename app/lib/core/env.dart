/// Build-time settings, passed with --dart-define.
///
///   flutter run --dart-define=USE_EMULATOR=true --dart-define=EMULATOR_HOST=192.168.100.10
class Env {
  /// Talk to the local Firebase emulators instead of production.
  static const useEmulator = bool.fromEnvironment('USE_EMULATOR');

  /// LAN address of the machine running `firebase emulators:start`.
  static const emulatorHost = String.fromEnvironment('EMULATOR_HOST', defaultValue: '10.0.2.2');

  /// Cloud Functions region (must match functions/src/index.ts).
  static const functionsRegion = 'asia-south1';

  /// Shown on the About screen.
  static const privacyUrl = String.fromEnvironment('PRIVACY_URL', defaultValue: 'https://medicalapps.homilabs.org/ecg-reader/privacy/');
}
