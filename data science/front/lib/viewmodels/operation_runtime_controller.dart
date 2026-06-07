library;

import '../models/job_record.dart';
import '../models/workbench_runtime_models.dart';
import 'operation_console_view_model.dart';
import 'shell_navigation_state.dart';
import 'shell_operation_session_controller.dart';

class OperationRuntimeController {
  OperationRuntimeController({
    required this.navigation,
    required this.operationConsoleViewModel,
    required this.operationSessionController,
  });

  final ShellNavigationState navigation;
  final OperationConsoleViewModel operationConsoleViewModel;
  final ShellOperationSessionController operationSessionController;

  Future<void> openOperation(
    String operationId, {
    JobRecord? seed,
    bool openPanel = true,
  }) async {
    operationSessionController.beginSelection(
      operationId: operationId,
      originTab: navigation.activeTab,
    );
    await operationConsoleViewModel.selectOperation(operationId, seed: seed);
    navigation.showPanel(ShellRuntimePanelKind.operations, visible: openPanel);
    syncActivity();
  }

  void focusOperation(JobRecord operation) {
    final operationId = operation.operationId ?? operation.jobId;
    if (operationConsoleViewModel.selectedOperationId != operationId) {
      operationSessionController.beginSelection(
        operationId: operationId,
        originTab: navigation.activeTab,
      );
    }
    navigation.showPanel(ShellRuntimePanelKind.operations);
    syncActivity();
  }

  void syncActivity() {
    final shouldStream =
        navigation.activeTab == WorkbenchTab.operationsHub ||
        (navigation.panelVisible &&
            navigation.panelKind == ShellRuntimePanelKind.operations);
    operationConsoleViewModel.setWorkspaceActive(shouldStream);
  }
}
