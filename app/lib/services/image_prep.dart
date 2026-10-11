import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;

/// On-device quality checks and preparation (design-v1 Sections 4, 9).
/// Output: JPEG, long edge at most 1600 px, orientation applied, NO EXIF
/// (no GPS, device or time data leaves the phone).
class PreparedImage {
  PreparedImage({required this.jpeg, required this.width, required this.height, required this.warnings});
  final Uint8List jpeg;
  final int width;
  final int height;
  final List<QualityWarning> warnings;
}

enum QualityWarning {
  blurry('The photo looks blurred. Hold the phone steady and tap to focus.'),
  glare('Strong glare or very bright patches. Avoid direct light on the paper.'),
  dark('The photo is dark. Use even light or the torch.'),
  lowResolution('The image is small. Move closer so the ECG fills the frame.');

  const QualityWarning(this.message);
  final String message;
}

class ImagePrepException implements Exception {
  ImagePrepException(this.message);
  final String message;
  @override
  String toString() => message;
}

class ImagePrep {
  static const maxLongEdge = 1600;

  /// Reads [path], prepares it in a background isolate, then deletes the file
  /// (camera, gallery and cropper copies are temporary).
  static Future<PreparedImage> prepareFile(String path) async {
    final file = File(path);
    try {
      final bytes = await file.readAsBytes();
      return await compute(prepareBytes, bytes);
    } finally {
      await deleteQuietly(path);
    }
  }

  static Future<void> deleteQuietly(String? path) async {
    if (path == null) return;
    try {
      final f = File(path);
      if (await f.exists()) await f.delete();
    } catch (_) {/* best effort */}
  }

  /// Pure function (runs in an isolate; also unit-tested).
  static PreparedImage prepareBytes(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) throw ImagePrepException('This file is not a supported image.');
    var image = img.bakeOrientation(decoded);
    final longEdge = math.max(image.width, image.height);
    if (longEdge > maxLongEdge) {
      image = image.width >= image.height
          ? img.copyResize(image, width: maxLongEdge, interpolation: img.Interpolation.average)
          : img.copyResize(image, height: maxLongEdge, interpolation: img.Interpolation.average);
    }
    image.exif = img.ExifData(); // drop every EXIF tag before encoding
    final warnings = assess(image, originalLongEdge: longEdge);
    final jpeg = img.encodeJpg(image, quality: 88);
    return PreparedImage(jpeg: jpeg, width: image.width, height: image.height, warnings: warnings);
  }

  /// Simple, conservative checks. They only warn; the doctor decides.
  static List<QualityWarning> assess(img.Image image, {required int originalLongEdge}) {
    final small = img.copyResize(img.grayscale(img.Image.from(image)), width: 480, interpolation: img.Interpolation.average);
    final w = small.width, h = small.height;
    final lum = List<double>.filled(w * h, 0);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        lum[y * w + x] = small.getPixel(x, y).r.toDouble();
      }
    }
    // Sharpness: variance of the Laplacian.
    var sum = 0.0, sumSq = 0.0;
    var n = 0;
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        final l = 4 * lum[y * w + x] - lum[y * w + x - 1] - lum[y * w + x + 1] - lum[(y - 1) * w + x] - lum[(y + 1) * w + x];
        sum += l;
        sumSq += l * l;
        n++;
      }
    }
    final mean = sum / n;
    final lapVar = sumSq / n - mean * mean;
    final avg = lum.reduce((a, b) => a + b) / lum.length;
    final saturated = lum.where((v) => v >= 252).length / lum.length;

    return [
      if (lapVar < 60) QualityWarning.blurry,
      if (saturated > 0.12) QualityWarning.glare,
      if (avg < 80) QualityWarning.dark,
      if (originalLongEdge < 900) QualityWarning.lowResolution,
    ];
  }
}
