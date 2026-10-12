// Lethal-rhythm check on the lead II strip (VT / VF / asystole vs other), on the phone.
// Our 1-D CNN trained on PhysioNet vfdb + cudb (ODC-By 1.0) and PTB-XL lead II (CC BY 4.0);
// input preparation is a port of prep() in validation/train_rhythm.py.
import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

import 'dsp.dart' show median;

/// (1, 1000): median removed, clipped to +/-5 mV.
Float32List rhythmInput(List<double> lead2) {
  final m = median(lead2);
  final out = Float32List(1000);
  for (var i = 0; i < 1000 && i < lead2.length; i++) {
    out[i] = (lead2[i] - m).clamp(-5.0, 5.0);
  }
  return out;
}

/// Softmax over logits.
List<double> softmax(List<double> z) {
  final m = z.reduce(math.max);
  final e = [for (final v in z) math.exp(v - m)];
  final s = e.reduce((a, b) => a + b);
  return [for (final v in e) v / s];
}

class RhythmResult {
  RhythmResult(this.probs, this.classes);
  final List<double> probs;
  final List<String> classes;
  double get pLethal => 1 - probs[0];

  /// Most likely lethal class (index >= 1).
  String get lethalClass {
    var k = 1;
    for (var i = 2; i < probs.length; i++) {
      if (probs[i] > probs[k]) k = i;
    }
    return classes[k];
  }
}

class RhythmModel {
  RhythmModel._(this._session, this.classes, this.lethalThreshold);
  final OrtSession _session;
  final List<String> classes;
  final double lethalThreshold;

  static Future<RhythmModel> load() async {
    final meta = jsonDecode(await rootBundle.loadString('assets/models/rhythm_meta.json')) as Map<String, dynamic>;
    final s = await OnnxRuntime().createSessionFromAsset('assets/models/rhythm.onnx');
    return RhythmModel._(s, (meta['classes'] as List).cast<String>(), (meta['lethal_threshold'] as num).toDouble());
  }

  Future<void> close() => _session.close();

  Future<RhythmResult> predict(List<double> lead2) async {
    final v = await OrtValue.fromList(rhythmInput(lead2), [1, 1, 1000]);
    final outs = await _session.run({_session.inputNames.first: v});
    final logits = await outs.values.first.asFlattenedList();
    await v.dispose();
    for (final o in outs.values) {
      await o.dispose();
    }
    return RhythmResult(softmax([for (final l in logits) (l as num).toDouble()]), classes);
  }
}
