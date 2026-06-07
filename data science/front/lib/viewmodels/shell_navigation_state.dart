library;

import 'package:flutter/foundation.dart';

import '../models/workbench_runtime_models.dart';

class ShellNavigationState extends ChangeNotifier {
  WorkbenchTab _activeTab = WorkbenchTab.operationsHub;
  bool _panelVisible = false;
  ShellRuntimePanelKind _panelKind = ShellRuntimePanelKind.approvals;

  WorkbenchTab get activeTab => _activeTab;
  bool get panelVisible => _panelVisible;
  ShellRuntimePanelKind get panelKind => _panelKind;

  void activateTab(WorkbenchTab tab) {
    if (_activeTab == tab) {
      return;
    }
    _activeTab = tab;
    notifyListeners();
  }

  void showPanel(ShellRuntimePanelKind kind, {bool visible = true}) {
    if (_panelKind == kind && _panelVisible == visible) {
      return;
    }
    _panelKind = kind;
    _panelVisible = visible;
    notifyListeners();
  }

  void closePanel() {
    if (!_panelVisible) {
      return;
    }
    _panelVisible = false;
    notifyListeners();
  }
}
