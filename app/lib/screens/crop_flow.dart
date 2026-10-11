import 'package:flutter/material.dart';
import 'package:image_cropper/image_cropper.dart';

import '../services/image_prep.dart';
import 'confirm_screen.dart';

/// Crop + rotate (removes the printed patient header), then prepare the image
/// in memory and delete every temporary file (design-v1 screen 4).
class CropFlow {
  static Future<void> start(BuildContext context, String sourcePath) async {
    final scheme = Theme.of(context).colorScheme;
    String? croppedPath;
    try {
      final cropped = await ImageCropper().cropImage(
        sourcePath: sourcePath,
        compressFormat: ImageCompressFormat.jpg,
        compressQuality: 95,
        maxWidth: 2400, // native downscale first: keeps on-device prep fast
        maxHeight: 2400,
        uiSettings: [
          AndroidUiSettings(
            toolbarTitle: 'Crop to the ECG trace',
            toolbarColor: scheme.primary,
            toolbarWidgetColor: scheme.onPrimary,
            activeControlsWidgetColor: scheme.primary,
            lockAspectRatio: false,
            initAspectRatio: CropAspectRatioPreset.original,
            aspectRatioPresets: const [CropAspectRatioPreset.original],
            showCropGrid: true,
          ),
        ],
      );
      croppedPath = cropped?.path;
    } finally {
      await ImagePrep.deleteQuietly(sourcePath);
    }
    if (croppedPath == null || !context.mounted) return;

    PreparedImage prepared;
    try {
      prepared = await ImagePrep.prepareFile(croppedPath); // also deletes the cropped file
    } on ImagePrepException catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      return;
    }
    if (!context.mounted) return;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConfirmScreen(image: prepared)));
  }
}
