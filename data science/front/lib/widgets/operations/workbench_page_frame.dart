library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

enum WorkbenchSurfaceMode { standalone, embedded }

extension WorkbenchSurfaceModeX on WorkbenchSurfaceMode {
  bool get isEmbedded => this == WorkbenchSurfaceMode.embedded;
  bool get isStandalone => this == WorkbenchSurfaceMode.standalone;
}

class WorkbenchPageFrame extends StatelessWidget {
  const WorkbenchPageFrame({
    super.key,
    required this.surfaceMode,
    required this.body,
    this.appBar,
    this.backgroundColor = AppColors.background,
  });

  final WorkbenchSurfaceMode surfaceMode;
  final Widget body;
  final PreferredSizeWidget? appBar;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    if (surfaceMode.isEmbedded) {
      return body;
    }

    return Scaffold(
      backgroundColor: backgroundColor,
      appBar: appBar,
      body: body,
    );
  }
}
