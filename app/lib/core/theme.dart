import 'package:flutter/material.dart';

/// Plain, fast, readable. Doctors are busy (design-v1 Section 9).
class AppTheme {
  static const seed = Color(0xFF00695C);

  static ThemeData light() => _base(Brightness.light);
  static ThemeData dark() => _base(Brightness.dark);

  static ThemeData _base(Brightness b) {
    final scheme = ColorScheme.fromSeed(seedColor: seed, brightness: b);
    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      appBarTheme: AppBarTheme(centerTitle: false, backgroundColor: scheme.surface),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), isDense: true),
    );
  }
}

/// Texts shown in more than one place.
class Copy {
  static const appName = 'ECG Reader';
  static const decisionSupport = 'Decision support only — your own reading of the ECG prevails.';
  static const disclaimerPoints = [
    'For qualified clinicians only. Not for patients or the public.',
    'Decision support only. It does not diagnose, and it can be wrong — including missing a dangerous pattern.',
    'Always read the ECG yourself and act on your own clinical judgment.',
    'Do not upload patient names, ID numbers or other identifying details. Crop the printed header away.',
    'Nothing is saved by this app or its server. The image is sent over an encrypted connection to an AI service '
        '(Anthropic) for reading, under that service\'s data terms.',
  ];
}
