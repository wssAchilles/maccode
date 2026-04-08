library;

enum WorkbenchTab {
  operationsHub,
  modeling,
  dataAnalysis,
  aiLab,
  historyAudit;

  int get tabIndex => WorkbenchTab.values.indexOf(this);

  static WorkbenchTab fromIndex(int index) {
    return WorkbenchTab.values[index.clamp(0, WorkbenchTab.values.length - 1)];
  }
}

enum JobFeedKey {
  optimization,
  analysis,
  mlTrain,
  ragIngest,
  historyAudit,
}

enum ShellRuntimePanelKind {
  approvals,
  operations,
  notifications,
}
