import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

/// Camera with a guide frame and placement hints (design-v1 screen 3).
/// Returns the path of the captured (temporary) photo.
class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});
  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> with WidgetsBindingObserver {
  CameraController? _ctrl;
  String? _error;
  bool _torch = false;
  bool _taking = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _open();
  }

  Future<void> _open() async {
    try {
      final cams = await availableCameras();
      final back = cams.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => cams.first);
      final ctrl = CameraController(back, ResolutionPreset.veryHigh, enableAudio: false, imageFormatGroup: ImageFormatGroup.jpeg);
      await ctrl.initialize();
      await ctrl.setFlashMode(FlashMode.off);
      if (!mounted) return ctrl.dispose();
      setState(() => _ctrl = ctrl);
    } on CameraException catch (e) {
      setState(() => _error = e.code == 'CameraAccessDenied' || e.code == 'CameraAccessDeniedWithoutPrompt'
          ? 'Camera permission is needed to scan an ECG. You can also choose a photo from the gallery.'
          : 'The camera could not be opened.');
    } catch (_) {
      setState(() => _error = 'No camera found on this device.');
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final c = _ctrl;
    if (c == null || !c.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      c.dispose();
      _ctrl = null;
    } else if (state == AppLifecycleState.resumed) {
      _open();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ctrl?.dispose();
    super.dispose();
  }

  Future<void> _toggleTorch() async {
    final c = _ctrl;
    if (c == null) return;
    _torch = !_torch;
    await c.setFlashMode(_torch ? FlashMode.torch : FlashMode.off);
    setState(() {});
  }

  Future<void> _shoot() async {
    final c = _ctrl;
    if (c == null || _taking) return;
    setState(() => _taking = true);
    try {
      final x = await c.takePicture();
      if (_torch) await c.setFlashMode(FlashMode.off);
      if (mounted) Navigator.of(context).pop(x.path);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not take the photo. Try again.')));
        setState(() => _taking = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _ctrl;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('Scan ECG'),
        actions: [
          if (c != null)
            IconButton(
              tooltip: _torch ? 'Torch off' : 'Torch on',
              icon: Icon(_torch ? Icons.flashlight_off : Icons.flashlight_on),
              onPressed: _toggleTorch,
            ),
        ],
      ),
      body: _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white)),
              ),
            )
          : c == null
              ? const Center(child: CircularProgressIndicator())
              : Column(children: [
                  Expanded(
                    child: Stack(fit: StackFit.expand, children: [
                      Center(child: CameraPreview(c)),
                      const IgnorePointer(child: CustomPaint(painter: _GuidePainter())),
                    ]),
                  ),
                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: _Hint(
                      'Place the ECG flat, in even light, without glare. Fill the frame with the trace. '
                      'Rotate the phone sideways for a wide 12-lead print.',
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: GestureDetector(
                      onTap: _shoot,
                      child: Semantics(
                        button: true,
                        label: 'Take photo',
                        child: Container(
                          width: 78,
                          height: 78,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 5),
                            color: _taking ? Colors.white54 : Colors.white24,
                          ),
                        ),
                      ),
                    ),
                  ),
                ]),
    );
  }
}

class _Hint extends StatelessWidget {
  const _Hint(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(10)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 13.5, height: 1.3)),
      );
}

/// Corner brackets marking where the ECG should sit.
class _GuidePainter extends CustomPainter {
  const _GuidePainter();
  @override
  void paint(Canvas canvas, Size size) {
    final r = Rect.fromLTRB(size.width * 0.05, size.height * 0.05, size.width * 0.95, size.height * 0.95);
    final p = Paint()
      ..color = Colors.white
      ..strokeWidth = 4
      ..style = PaintingStyle.stroke;
    const l = 36.0;
    for (final (o, dx, dy) in [
      (r.topLeft, 1.0, 1.0),
      (r.topRight, -1.0, 1.0),
      (r.bottomLeft, 1.0, -1.0),
      (r.bottomRight, -1.0, -1.0),
    ]) {
      canvas.drawLine(o, o + Offset(l * dx, 0), p);
      canvas.drawLine(o, o + Offset(0, l * dy), p);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
