import 'dart:async';
import 'dart:convert';

import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import '../core/env.dart';
import '../models/clinical_context.dart';
import '../models/ecg_result.dart';

/// A failure the user can understand and maybe fix.
class EcgApiException implements Exception {
  EcgApiException(this.message, {this.retryable = true});
  final String message;
  final bool retryable;
  @override
  String toString() => message;
}

/// Calls the two Cloud Functions. Nothing is cached or stored.
class EcgApi {
  EcgApi._();
  static final instance = EcgApi._();

  FirebaseFunctions get _fns => FirebaseFunctions.instanceFor(region: Env.functionsRegion);

  /// Anonymous sign-in: invisible to the doctor, used only for rate limiting.
  Future<void> ensureSignedIn() async {
    final auth = FirebaseAuth.instance;
    if (auth.currentUser == null) await auth.signInAnonymously();
  }

  Future<EcgResult> interpret(Uint8List jpeg) async {
    final data = await _call(
      'interpretEcg',
      {'image': base64Encode(jpeg), 'mediaType': 'image/jpeg'},
      const Duration(seconds: 150),
    );
    return EcgResult.fromResponse(data);
  }

  Future<ContextAssessment> reassess(EcgResult result, ClinicalContext ctx) async {
    final data = await _call(
      'reassessWithContext',
      {'reading': result.readingJson, 'context': ctx.toJson()},
      const Duration(seconds: 30),
    );
    return ContextAssessment.fromResponse(data);
  }

  Future<Map<String, dynamic>> _call(String name, Map<String, dynamic> body, Duration timeout) async {
    try {
      await ensureSignedIn();
      final callable = _fns.httpsCallable(name, options: HttpsCallableOptions(timeout: timeout));
      final res = await callable.call<Object?>(body).timeout(timeout + const Duration(seconds: 5));
      final d = res.data;
      if (d is! Map) throw EcgApiException('Unexpected reply from the server.');
      return _deepMap(d);
    } on FirebaseFunctionsException catch (e) {
      debugPrint('$name failed: ${e.code} ${e.message}');
      throw EcgApiException(_message(e), retryable: _retryable(e.code));
    } on FirebaseAuthException catch (e) {
      throw EcgApiException(
        e.code == 'network-request-failed'
            ? 'No internet connection. ECG reading needs internet.'
            : 'Could not start a session. Please try again.',
      );
    } on TimeoutException {
      throw EcgApiException('The reading took too long. Check your connection and try again.');
    }
  }

  static bool _retryable(String code) =>
      !{'invalid-argument', 'failed-precondition', 'resource-exhausted', 'permission-denied'}.contains(code);

  static String _message(FirebaseFunctionsException e) {
    switch (e.code) {
      case 'unavailable':
        return e.message?.isNotEmpty == true && !e.message!.contains('UNAVAILABLE')
            ? e.message!
            : 'The reading service is unavailable or there is no internet. Please try again.';
      case 'deadline-exceeded':
        return 'The reading took too long. Please try again.';
      case 'resource-exhausted':
      case 'invalid-argument':
      case 'failed-precondition':
        return e.message ?? 'The request could not be processed.';
      case 'unauthenticated':
      case 'permission-denied':
        return 'This copy of the app could not be verified. Please install it from Google Play.';
      default:
        return 'Reading failed. Please try again.';
    }
  }

  static Map<String, dynamic> _deepMap(Map m) => m.map((k, v) => MapEntry(k.toString(), _deep(v)));
  static Object? _deep(Object? v) => v is Map ? _deepMap(v) : (v is List ? v.map(_deep).toList() : v);
}
