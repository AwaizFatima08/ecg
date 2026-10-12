// Signal -> findings classifier (our 1-D CNN, trained on PTB-XL; ONNX), on the phone.
// Input preparation is a port of paper_view() in validation/train_classifier.py.
import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

import 'dsp.dart' show median;
import 'measure.dart' show column;

/// (13, 1000): 12 leads visible only in their 3x4 print window, each segment baseline-removed,
/// plus a visibility channel. Values clipped to +/-5 mV.
Float32List paperView(List<List<double>> x) {
  final mask = List.generate(12, (j) => List<bool>.generate(1000, (i) => j == 1 || (i ~/ 250) == column[j]));
  final out = Float32List(13 * 1000);
  for (var j = 0; j < 12; j++) {
    final seg = [for (var i = 0; i < 1000; i++) if (mask[j][i]) x[j][i]];
    final m = median(seg);
    for (var i = 0; i < 1000; i++) {
      if (mask[j][i]) out[j * 1000 + i] = (x[j][i] - m).clamp(-5.0, 5.0);
    }
  }
  for (var i = 0; i < 1000; i++) {
    var s = 0.0;
    for (var j = 0; j < 12; j++) {
      if (mask[j][i]) s += 1;
    }
    out[12 * 1000 + i] = s / 12;
  }
  return out;
}

/// One or more classifiers (an ensemble listed in ecgnet_meta.json under "models"); their
/// probabilities are averaged and compared with the ensemble's own thresholds.
class Classifier {
  Classifier._(this._sessions, this.labels, this.thresholds);
  final List<OrtSession> _sessions;
  final List<String> labels;
  final Map<String, double> thresholds;

  static Future<Classifier> load() async {
    final meta = jsonDecode(await rootBundle.loadString('assets/models/ecgnet_meta.json')) as Map<String, dynamic>;
    final files = (meta['models'] as List?)?.cast<String>() ?? const ['ecgnet.onnx'];
    final sessions = [
      for (final f in files) await OnnxRuntime().createSessionFromAsset('assets/models/$f'),
    ];
    return Classifier._(
      sessions,
      (meta['labels'] as List).cast<String>(),
      (meta['thresholds'] as Map).map((k, v) => MapEntry(k as String, (v as num).toDouble())),
    );
  }

  Future<void> close() async {
    for (final s in _sessions) {
      await s.close();
    }
  }

  /// Probability per label (mean over the ensemble).
  Future<Map<String, double>> predict(List<List<double>> x) async {
    final input = paperView(x);
    final sum = List<double>.filled(labels.length, 0);
    for (final s in _sessions) {
      final v = await OrtValue.fromList(input, [1, 13, 1000]);
      final outs = await s.run({s.inputNames.first: v});
      final logits = await outs.values.first.asFlattenedList();
      await v.dispose();
      for (final o in outs.values) {
        await o.dispose();
      }
      for (var k = 0; k < labels.length; k++) {
        sum[k] += 1 / (1 + math.exp(-(logits[k] as num).toDouble()));
      }
    }
    return {for (var k = 0; k < labels.length; k++) labels[k]: sum[k] / _sessions.length};
  }
}
