library;

import 'motion_tokens.dart';

class StaggerSpec {
  const StaggerSpec({
    this.step = const Duration(milliseconds: 36),
    this.initialDelay = Duration.zero,
  });

  final Duration step;
  final Duration initialDelay;

  Duration delayFor(int index) {
    return initialDelay + (step * index);
  }

  static const cards = StaggerSpec(step: Duration(milliseconds: 42));
  static const statusItems = StaggerSpec(step: Duration(milliseconds: 24));
  static const none = StaggerSpec(step: Duration.zero);
}

extension DurationScale on Duration {
  Duration operator *(int factor) {
    if (factor <= 0) {
      return Duration.zero;
    }
    return Duration(microseconds: inMicroseconds * factor);
  }
}

const defaultMotionDuration = MotionTokens.standard;
