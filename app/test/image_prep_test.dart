import 'dart:typed_data';

import 'package:ecg_reader/services/image_prep.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

/// ECG-like test card: pale paper, pink grid, dark zig-zag trace.
img.Image ecgCard(int w, int h) {
  final im = img.Image(width: w, height: h);
  img.fill(im, color: img.ColorRgb8(250, 245, 246));
  for (var x = 0; x < w; x += 8) {
    img.drawLine(im, x1: x, y1: 0, x2: x, y2: h - 1, color: img.ColorRgb8(240, 190, 200));
  }
  for (var y = 0; y < h; y += 8) {
    img.drawLine(im, x1: 0, y1: y, x2: w - 1, y2: y, color: img.ColorRgb8(240, 190, 200));
  }
  for (var x = 0; x < w - 20; x += 20) {
    img.drawLine(im, x1: x, y1: h ~/ 2, x2: x + 10, y2: h ~/ 2 - 60, color: img.ColorRgb8(30, 30, 30), thickness: 3);
    img.drawLine(im, x1: x + 10, y1: h ~/ 2 - 60, x2: x + 20, y2: h ~/ 2, color: img.ColorRgb8(30, 30, 30), thickness: 3);
  }
  return im;
}

void main() {
  test('removes EXIF (GPS, device) and keeps a decodable JPEG', () {
    final src = ecgCard(1200, 800);
    src.exif.imageIfd['Make'] = 'PhoneMaker';
    src.exif.imageIfd['Model'] = 'Secret Model';
    src.exif.gpsIfd['GPSLatitude'] = img.IfdValueRational(31, 1);
    final withExif = img.encodeJpg(src);
    expect(img.decodeJpg(withExif)!.exif.isEmpty, isFalse, reason: 'fixture should carry EXIF');

    final out = ImagePrep.prepareBytes(withExif);
    final decoded = img.decodeJpg(out.jpeg)!;
    expect(decoded.exif.isEmpty, isTrue);
    expect(String.fromCharCodes(out.jpeg).contains('Secret Model'), isFalse);
  });

  test('resizes the long edge to 1600 px, keeps aspect', () {
    final out = ImagePrep.prepareBytes(img.encodeJpg(ecgCard(4000, 3000)));
    expect(out.width, 1600);
    expect(out.height, 1200);
  });

  test('does not upscale small images and warns about them', () {
    final out = ImagePrep.prepareBytes(img.encodeJpg(ecgCard(800, 600)));
    expect(out.width, 800);
    expect(out.warnings, contains(QualityWarning.lowResolution));
  });

  test('a sharp, well-lit ECG card has no quality warnings', () {
    final out = ImagePrep.prepareBytes(img.encodeJpg(ecgCard(2000, 1400)));
    expect(out.warnings, isEmpty);
  });

  test('blur and darkness are detected', () {
    final blurred = img.gaussianBlur(ecgCard(2000, 1400), radius: 12);
    expect(ImagePrep.prepareBytes(img.encodeJpg(blurred)).warnings, contains(QualityWarning.blurry));
    final dark = img.adjustColor(ecgCard(2000, 1400), brightness: 0.25);
    expect(ImagePrep.prepareBytes(img.encodeJpg(dark)).warnings, contains(QualityWarning.dark));
  });

  test('glare (large blown-out area) is detected', () {
    final im = ecgCard(2000, 1400);
    img.fillCircle(im, x: 1000, y: 700, radius: 450, color: img.ColorRgb8(255, 255, 255));
    expect(ImagePrep.prepareBytes(img.encodeJpg(im)).warnings, contains(QualityWarning.glare));
  });

  test('rejects non-images', () {
    expect(() => ImagePrep.prepareBytes(Uint8List.fromList(List.filled(500, 7))), throwsA(isA<ImagePrepException>()));
  });
}
