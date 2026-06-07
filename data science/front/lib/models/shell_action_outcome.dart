library;

enum ShellActionTone { success, warning, error, info }

class ShellActionOutcome<T> {
  const ShellActionOutcome({
    required this.message,
    required this.tone,
    this.data,
  });

  final String message;
  final ShellActionTone tone;
  final T? data;

  bool get succeeded => tone != ShellActionTone.error;

  static ShellActionOutcome<T> success<T>(
    String message, {
    T? data,
    ShellActionTone tone = ShellActionTone.success,
  }) {
    return ShellActionOutcome<T>(message: message, tone: tone, data: data);
  }

  static ShellActionOutcome<T> failure<T>(String message, {T? data}) {
    return ShellActionOutcome<T>(
      message: message,
      tone: ShellActionTone.error,
      data: data,
    );
  }
}
