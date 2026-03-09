/// AI Lab 跳转意图
library;

enum AiLabLaunchTarget { deepLearning, rag }

class AiLabLaunchIntent {
  const AiLabLaunchIntent({
    required this.target,
    required this.storagePath,
  });

  final AiLabLaunchTarget target;
  final String storagePath;

  factory AiLabLaunchIntent.deepLearning(String storagePath) {
    return AiLabLaunchIntent(
      target: AiLabLaunchTarget.deepLearning,
      storagePath: storagePath,
    );
  }

  factory AiLabLaunchIntent.rag(String storagePath) {
    return AiLabLaunchIntent(
      target: AiLabLaunchTarget.rag,
      storagePath: storagePath,
    );
  }
}
