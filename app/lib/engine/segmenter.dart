// Segmentation U-Net (Open-ECG-Digitizer weights, CC BY-SA 4.0; int8 ONNX) run on the phone.
// Port of Segmenter.tiled + segment() in validation/lite_digitizer.py.
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';
import 'package:image/image.dart' as img;

import 'digitizer.dart' show Map2D;

const _gridClass = 0, _signalClass = 2;

/// RGB image normalised to [0, 1] by its global min/max, long side [size] px, channel-planar (CHW).
class PreparedTensor {
  PreparedTensor(this.chw, this.w, this.h);
  final Float32List chw;
  final int w, h;
}

PreparedTensor prepareImage(Uint8List jpeg, {int size = 1600}) {
  var im = img.decodeImage(jpeg);
  if (im == null) throw ArgumentError('not an image');
  im = img.bakeOrientation(im);
  final long = math.max(im.width, im.height);
  if (long != size) {
    final s = size / long;
    im = img.copyResize(im, width: (im.width * s).toInt(), height: (im.height * s).toInt(),
        interpolation: img.Interpolation.average);
  }
  final w = im.width, h = im.height;
  final chw = Float32List(3 * w * h);
  var lo = 255.0, hi = 0.0;
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final p = im.getPixel(x, y);
      final r = p.r.toDouble(), g = p.g.toDouble(), b = p.b.toDouble();
      chw[y * w + x] = r;
      chw[w * h + y * w + x] = g;
      chw[2 * w * h + y * w + x] = b;
      lo = math.min(lo, math.min(r, math.min(g, b)));
      hi = math.max(hi, math.max(r, math.max(g, b)));
    }
  }
  final span = hi - lo + 1e-9;
  for (var i = 0; i < chw.length; i++) {
    chw[i] = (chw[i] - lo) / span;
  }
  return PreparedTensor(chw, w, h);
}

class Segmenter {
  Segmenter._(this._session);
  final OrtSession _session;

  static Future<Segmenter> load({String asset = 'assets/models/unet_int8.onnx'}) async {
    final s = await OnnxRuntime().createSessionFromAsset(asset,
        options: OrtSessionOptions(intraOpNumThreads: 4));
    return Segmenter._(s);
  }

  Future<void> close() => _session.close();

  /// Returns (signal, grid) probability maps (sparse-normalised) at the prepared image size.
  /// The U-Net runs on overlapping [tile]-px tiles to keep phone memory bounded.
  Future<(Map2D, Map2D)> run(PreparedTensor t, {int tile = 768, int overlap = 64}) async {
    final w = t.w, h = t.h;
    final pw = ((w + 127) ~/ 128) * 128, ph = ((h + 127) ~/ 128) * 128;
    final sig = Map2D(w, h), grid = Map2D(w, h);
    final tw = math.min(tile, pw), th = math.min(tile, ph);
    final step = tile - overlap;
    List<int> starts(int full, int tl) {
      final s = <int>[];
      for (var v = 0; v <= math.max(1, full - tl); v += step) {
        s.add(v);
      }
      if (s.isEmpty) s.add(0);
      if (s.last + tl < full) s.add(full - tl);
      return s;
    }

    final inName = _session.inputNames.first;
    for (final y0 in starts(ph, th)) {
      for (final x0 in starts(pw, tw)) {
        final input = Float32List(3 * tw * th);
        for (var c = 0; c < 3; c++) {
          for (var y = 0; y < th; y++) {
            final sy = y0 + y;
            if (sy >= h) continue;
            for (var x = 0; x < tw; x++) {
              final sx = x0 + x;
              if (sx >= w) continue;
              input[c * tw * th + y * tw + x] = t.chw[c * w * h + sy * w + sx];
            }
          }
        }
        final v = await OrtValue.fromList(input, [1, 3, th, tw]);
        final outs = await _session.run({inName: v});
        final logits = await outs.values.first.asFlattenedList();
        await v.dispose();
        for (final o in outs.values) {
          await o.dispose();
        }
        final a = y0 > 0 ? overlap ~/ 2 : 0, b = x0 > 0 ? overlap ~/ 2 : 0;
        final plane = tw * th;
        for (var y = a; y < th; y++) {
          final gy = y0 + y;
          if (gy >= h) continue;
          for (var x = b; x < tw; x++) {
            final gx = x0 + x;
            if (gx >= w) continue;
            final k = y * tw + x;
            final l0 = (logits[k] as num).toDouble(), l1 = (logits[plane + k] as num).toDouble();
            final l2 = (logits[2 * plane + k] as num).toDouble(), l3 = (logits[3 * plane + k] as num).toDouble();
            final m = math.max(math.max(l0, l1), math.max(l2, l3));
            final e0 = math.exp(l0 - m), e1 = math.exp(l1 - m), e2 = math.exp(l2 - m), e3 = math.exp(l3 - m);
            final s = e0 + e1 + e2 + e3;
            sig.d[gy * w + gx] = [e0, e1, e2, e3][_signalClass] / s;
            grid.d[gy * w + gx] = [e0, e1, e2, e3][_gridClass] / s;
          }
        }
      }
    }
    _sparse(sig);
    _sparse(grid);
    return (sig, grid);
  }

  static void _sparse(Map2D m) {
    var sum = 0.0;
    for (final v in m.d) {
      sum += v;
    }
    final mean = sum / m.d.length;
    var mx = 0.0;
    for (var i = 0; i < m.d.length; i++) {
      final v = math.max(0.0, m.d[i] - mean);
      m.d[i] = v;
      if (v > mx) mx = v;
    }
    for (var i = 0; i < m.d.length; i++) {
      m.d[i] = m.d[i] / (mx + 1e-9);
    }
  }
}
