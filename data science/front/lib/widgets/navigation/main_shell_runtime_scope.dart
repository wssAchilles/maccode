library;

import 'package:flutter/widgets.dart';

import '../../viewmodels/main_shell_runtime_view_model.dart';

class MainShellRuntimeScope extends InheritedNotifier<MainShellRuntimeViewModel> {
  const MainShellRuntimeScope({
    super.key,
    required MainShellRuntimeViewModel runtime,
    required super.child,
  }) : super(notifier: runtime);

  static MainShellRuntimeViewModel of(BuildContext context) {
    final scope = context
        .dependOnInheritedWidgetOfExactType<MainShellRuntimeScope>();
    assert(scope != null, 'MainShellRuntimeScope is missing in this subtree.');
    return scope!.notifier!;
  }

  static MainShellRuntimeViewModel? maybeOf(BuildContext context) {
    final element = context.getElementForInheritedWidgetOfExactType<
        MainShellRuntimeScope>();
    final widget = element?.widget;
    if (widget is! MainShellRuntimeScope) {
      return null;
    }
    return widget.notifier;
  }
}
