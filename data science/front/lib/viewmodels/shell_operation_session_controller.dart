library;

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../models/shell_operation_session.dart';
import '../models/workbench_runtime_models.dart';
import 'operation_console_view_model.dart';

class ShellOperationSessionController extends ChangeNotifier {
  ShellOperationSession _session = const ShellOperationSession.idle();

  ShellOperationSession get session => _session;

  void beginSelection({
    required String operationId,
    required WorkbenchTab originTab,
  }) {
    _session = ShellOperationSession(
      sessionId: 'session-$operationId',
      operationId: operationId,
      originTab: originTab,
      openedAt: DateTime.now(),
      lastUpdatedAt: DateTime.now(),
      phase: ShellOperationSessionPhase.loading,
      latestMessage: '正在载入运行详情',
    );
    notifyListeners();
  }

  void syncFromConsole(OperationConsoleViewModel viewModel) {
    final operation = viewModel.selectedOperation;
    if (operation == null && _session.operationId == null) {
      return;
    }
    if (operation == null) {
      _session = const ShellOperationSession.idle();
      notifyListeners();
      return;
    }

    final projection = operation.sessionProjection;
    final latestMessage =
        projection?.latestEventMessage ??
        operation.latestEvent?.message ??
        operation.statusMessage ??
        operation.currentStep?.message;
    final nextPhase = _phaseFor(viewModel, operation);
    final nextSession = ShellOperationSession(
      sessionId: _session.sessionId.isEmpty
          ? 'session-${operation.operationId ?? operation.jobId}'
          : _session.sessionId,
      operationId: operation.operationId ?? operation.jobId,
      originTab: _session.originTab,
      openedAt: _session.openedAt ?? DateTime.now(),
      lastUpdatedAt:
          projection?.lastTransitionAt ??
          projection?.latestEventAt ??
          operation.completedAt ??
          operation.startedAt ??
          operation.submittedAt ??
          DateTime.now(),
      phase: nextPhase,
      operation: operation,
      latestMessage: latestMessage,
      errorMessage: viewModel.errorMessage,
      streaming: viewModel.isStreaming,
      retainedAcrossTabs: true,
    );
    if (_sessionEquals(_session, nextSession)) {
      return;
    }
    _session = nextSession;
    notifyListeners();
  }

  void clear() {
    if (_session.operationId == null) {
      return;
    }
    _session = const ShellOperationSession.idle();
    notifyListeners();
  }

  ShellOperationSessionPhase _phaseFor(
    OperationConsoleViewModel viewModel,
    JobRecord operation,
  ) {
    if (viewModel.errorMessage != null && viewModel.errorMessage!.isNotEmpty) {
      return ShellOperationSessionPhase.error;
    }
    if (viewModel.isLoading) {
      return ShellOperationSessionPhase.loading;
    }
    if (viewModel.isActing) {
      return ShellOperationSessionPhase.acting;
    }
    if (operation.isAwaitingApproval) {
      return ShellOperationSessionPhase.awaitingApproval;
    }
    if (operation.isTerminal || operation.sessionProjection?.terminal == true) {
      return ShellOperationSessionPhase.terminal;
    }
    return ShellOperationSessionPhase.live;
  }

  bool _sessionEquals(ShellOperationSession left, ShellOperationSession right) {
    return left.operationId == right.operationId &&
        left.phase == right.phase &&
        left.streaming == right.streaming &&
        left.errorMessage == right.errorMessage &&
        left.latestMessage == right.latestMessage &&
        left.lastUpdatedAt == right.lastUpdatedAt &&
        identical(left.operation, right.operation);
  }
}
