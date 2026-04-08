library;

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../models/shell_action_outcome.dart';
import '../models/shell_runtime_action_state.dart';
import '../models/shell_runtime_intent.dart';

class ShellRuntimeActionStateMachine extends ChangeNotifier {
  static const int _historyLimit = 12;

  ShellRuntimeActionState? _activeAction;
  final List<ShellRuntimeActionState> _recentActions =
      <ShellRuntimeActionState>[];

  ShellRuntimeActionState? get activeAction => _activeAction;
  List<ShellRuntimeActionState> get recentActions =>
      List.unmodifiable(_recentActions);
  bool get hasActiveAction => _activeAction != null;

  Future<ShellActionOutcome<T>> dispatch<T>({
    required ShellRuntimeIntent intent,
    required Future<ShellActionOutcome<T>> Function() run,
  }) async {
    final initialPhase = switch (intent.kind) {
      ShellIntentKind.retryOperation => ShellActionPhase.replaying,
      _ => ShellActionPhase.submitting,
    };
    _activeAction = ShellRuntimeActionState(
      intent: intent,
      phase: initialPhase,
      startedAt: DateTime.now(),
      message: intent.summary,
      tone: ShellActionTone.info,
    );
    notifyListeners();

    late final ShellActionOutcome<T> outcome;
    try {
      outcome = await run();
    } catch (error) {
      outcome = ShellActionOutcome.failure<T>('控制动作失败: $error');
    }
    final completedAt = DateTime.now();
    final relatedOperationId = _extractOperationId(outcome.data);
    final phase = _resolveCompletedPhase(outcome);
    final completed = _activeAction!.copyWith(
      phase: phase,
      completedAt: completedAt,
      message: outcome.message,
      tone: outcome.tone,
      relatedOperationId: relatedOperationId,
    );
    _activeAction = null;
    _recentActions.insert(0, completed);
    if (_recentActions.length > _historyLimit) {
      _recentActions.removeRange(_historyLimit, _recentActions.length);
    }
    notifyListeners();
    return outcome;
  }

  ShellActionPhase _resolveCompletedPhase<T>(ShellActionOutcome<T> outcome) {
    if (!outcome.succeeded) {
      return ShellActionPhase.failed;
    }
    final data = outcome.data;
    if (data is JobRecord && data.isAwaitingApproval) {
      return ShellActionPhase.awaitingApproval;
    }
    return ShellActionPhase.succeeded;
  }

  String? _extractOperationId<T>(T? data) {
    if (data is JobRecord) {
      return data.operationId ?? data.jobId;
    }
    return null;
  }
}
