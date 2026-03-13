library;

import '../models/dashboard_summary.dart';
import '../models/workbench_launch_context.dart';

AssetChainSummary? selectPriorityChain(AssetSummary? summary) {
  final chains = summary?.chainSummaries;
  if (chains == null || chains.isEmpty) {
    return null;
  }
  return ([...chains]..sort((a, b) => b.priorityScore.compareTo(a.priorityScore)))
      .first;
}

bool isDutyFocusChain(AssetChainSummary? chain, DutySummary? dutySummary) {
  final focusKey = dutySummary?.focusChainKey;
  if (chain == null || focusKey == null || focusKey.isEmpty) {
    return false;
  }
  return chain.key == focusKey;
}

int compareChainsByDutyFocus(
  AssetChainSummary? a,
  AssetChainSummary? b,
  DutySummary? dutySummary,
) {
  final focusKey = dutySummary?.focusChainKey;
  if (focusKey != null && focusKey.isNotEmpty) {
    final aFocused = a?.key == focusKey ? 1 : 0;
    final bFocused = b?.key == focusKey ? 1 : 0;
    if (aFocused != bFocused) {
      return bFocused.compareTo(aFocused);
    }
  }
  return (b?.priorityScore ?? 0).compareTo(a?.priorityScore ?? 0);
}

String buildChainSourceLabel(
  AssetChainSummary? chain, {
  required String prefix,
  bool includeChainLabel = true,
  bool includeWorkspace = true,
  bool includeCardTarget = true,
  bool includeIncident = true,
  bool includeWorkspaceBrief = false,
  bool includeSection = false,
  bool includeFocus = false,
}) {
  if (chain == null) {
    return prefix;
  }

  return _joinContextParts([
    prefix,
    if (includeChainLabel) chain.label,
    if (includeWorkspace) chain.workspaceTargetLabel,
    if (includeCardTarget) chain.cardTargetLabel,
    if (includeIncident) chain.incidentTargetLabel,
    if (includeWorkspaceBrief) chain.workspaceBrief,
    if (includeSection) chain.sectionTargetLabel,
    if (includeFocus) chain.focusLabel,
  ]);
}

String buildChainFeedbackMessage(
  AssetChainSummary? chain, {
  required String prefix,
  String? detail,
}) {
  return _joinContextParts([
    prefix,
    chain?.workspaceTargetLabel,
    chain?.cardTargetLabel,
    chain?.incidentTargetLabel,
    detail,
  ]);
}

String buildDutyActionSourceLabel(
  DutyAction action, {
  required String prefix,
  bool includeChainLabel = true,
  bool includeWorkspaceBrief = true,
}) {
  return _joinContextParts([
    prefix,
    if (includeChainLabel) action.chainLabel,
    action.workspaceTargetLabel,
    action.cardTargetLabel,
    action.incidentTargetLabel,
    if (includeWorkspaceBrief) action.workspaceBrief,
  ]);
}

WorkbenchLaunchContext? buildLaunchContextFromChain(
  AssetChainSummary? chain, {
  required String prefix,
}) {
  if (chain == null) {
    return null;
  }
  return WorkbenchLaunchContext(
    sourceLabel: buildChainSourceLabel(
      chain,
      prefix: prefix,
      includeWorkspace: false,
      includeCardTarget: false,
      includeIncident: false,
      includeWorkspaceBrief: false,
    ),
    workspaceTarget: chain.workspaceTarget,
    workspaceTargetLabel: chain.workspaceTargetLabel,
    cardTarget: chain.cardTarget,
    cardTargetLabel: chain.cardTargetLabel,
    incidentTarget: chain.incidentTarget,
    incidentTargetLabel: chain.incidentTargetLabel,
    workspaceBrief: chain.workspaceBrief,
    watchSummary: chain.incidentBrief,
  );
}

WorkbenchLaunchContext buildLaunchContextFromDutyAction(
  DutyAction action, {
  required String prefix,
}) {
  return WorkbenchLaunchContext(
    sourceLabel: _joinContextParts([
      prefix,
      action.chainLabel,
    ]),
    workspaceTarget: action.workspaceTarget,
    workspaceTargetLabel: action.workspaceTargetLabel,
    cardTarget: action.cardTarget,
    cardTargetLabel: action.cardTargetLabel,
    incidentTarget: action.incidentTarget,
    incidentTargetLabel: action.incidentTargetLabel,
    workspaceBrief: action.workspaceBrief,
    watchSummary: _joinContextParts([
      action.incidentTargetLabel,
      action.workspaceBrief,
    ]),
  );
}

String buildLaunchArrivalMessage(
  WorkbenchLaunchContext? context, {
  required String fallbackSubject,
  required String destination,
  String verb = '已打开',
}) {
  final subject = (context?.sourceLabel ?? fallbackSubject).trim();
  if (context == null) {
    return '$subject$verb$destination';
  }
  return _joinContextParts([
    '$subject$verb$destination',
    context.workspaceTargetLabel,
    context.cardTargetLabel,
    context.workspaceBrief,
  ]);
}

String buildChainCurrentWatch(
  AssetChainSummary? chain, {
  String fallback = '当前暂无链路焦点。',
}) {
  if (chain == null) {
    return fallback;
  }
  return _joinContextParts([
    chain.workspaceTargetLabel,
    chain.cardTargetLabel,
    chain.workspaceBrief,
  ]);
}

String _joinContextParts(List<String?> parts) {
  final filtered = parts
      .whereType<String>()
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
  return filtered.join(' · ');
}
