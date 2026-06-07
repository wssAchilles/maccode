library;

import 'package:flutter/widgets.dart';

class MotionTokens {
  const MotionTokens._();

  static const Duration fast = Duration(milliseconds: 160);
  static const Duration standard = Duration(milliseconds: 220);
  static const Duration emphasized = Duration(milliseconds: 320);

  static const Curve easeOut = Curves.easeOutCubic;
  static const Curve easeInOut = Curves.easeInOutCubic;

  static const double hoverScale = 1.02;
}

class ReducedMotionPolicy {
  const ReducedMotionPolicy({required this.disableTransformMotion});

  factory ReducedMotionPolicy.fromContext(BuildContext context) {
    return ReducedMotionPolicy(
      disableTransformMotion: MediaQuery.disableAnimationsOf(context),
    );
  }

  final bool disableTransformMotion;
}
