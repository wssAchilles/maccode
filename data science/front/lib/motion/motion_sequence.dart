library;

import 'package:flutter/animation.dart';

import 'motion_tokens.dart';

class MotionSequence {
  const MotionSequence({
    this.duration = MotionTokens.standard,
    this.curve = MotionTokens.easeOut,
  });

  final Duration duration;
  final Curve curve;

  Animation<double> drive(AnimationController controller) {
    return CurvedAnimation(parent: controller, curve: curve);
  }
}
