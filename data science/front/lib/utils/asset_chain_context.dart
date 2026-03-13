library;

import '../models/dashboard_summary.dart';
import '../models/workbench_launch_context.dart';

AssetChainSummary? selectPriorityChain(AssetSummary? summary) {
  final chains = summary?.chainSummaries;
  if (chains == null || chains.isEmpty) {
    return null;
  }
  return ([
    ...chains,
  ]..sort((a, b) => b.priorityScore.compareTo(a.priorityScore))).first;
}

AssetChainSummary? selectDutyFocusChain(
  AssetSummary? summary,
  DutySummary? dutySummary,
) {
  final focusKey = dutySummary?.focusChainKey;
  if (focusKey != null && focusKey.isNotEmpty) {
    final chain = findChainSummary(summary, focusKey);
    if (chain != null) {
      return chain;
    }
  }
  return selectPriorityChain(summary);
}

AssetChainSummary? findChainSummary(AssetSummary? summary, String key) {
  final chains = summary?.chainSummaries;
  if (chains == null || chains.isEmpty || key.isEmpty) {
    return null;
  }
  for (final chain in chains) {
    if (chain.key == key) {
      return chain;
    }
  }
  return null;
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

WorkbenchLaunchContext buildLaunchContext({
  required String sourceLabel,
  AssetChainSummary? chain,
  WorkbenchLaunchContext? base,
  String? workspaceTarget,
  String? cardTarget,
  String? incidentTarget,
  String? workspaceBrief,
  String? watchSummary,
}) {
  final resolvedWorkspaceTarget =
      workspaceTarget ??
      base?.workspaceTarget ??
      chain?.workspaceTarget ??
      'workspace';
  final resolvedCardTarget =
      cardTarget ?? base?.cardTarget ?? chain?.cardTarget ?? 'summary';
  final resolvedIncidentTarget =
      incidentTarget ??
      base?.incidentTarget ??
      chain?.incidentTarget ??
      'focus';
  final resolvedWorkspaceBrief =
      workspaceBrief ??
      base?.workspaceBrief ??
      chain?.workspaceBrief ??
      '已进入当前工作台。';
  final resolvedWatchSummary =
      watchSummary ??
      base?.watchSummary ??
      chain?.incidentBrief ??
      resolvedWorkspaceBrief;

  return WorkbenchLaunchContext(
    sourceLabel: sourceLabel,
    workspaceTarget: resolvedWorkspaceTarget,
    workspaceTargetLabel:
        _workspaceTargetLabel(resolvedWorkspaceTarget) ??
        base?.workspaceTargetLabel ??
        chain?.workspaceTargetLabel ??
        '工作台',
    cardTarget: resolvedCardTarget,
    cardTargetLabel:
        _cardTargetLabel(resolvedCardTarget) ??
        base?.cardTargetLabel ??
        chain?.cardTargetLabel ??
        '当前卡片',
    incidentTarget: resolvedIncidentTarget,
    incidentTargetLabel:
        _incidentTargetLabel(resolvedIncidentTarget) ??
        base?.incidentTargetLabel ??
        chain?.incidentTargetLabel ??
        '当前焦点',
    workspaceBrief: resolvedWorkspaceBrief,
    watchSummary: resolvedWatchSummary,
  );
}

WorkbenchLaunchContext buildLaunchContextFromDutyAction(
  DutyAction action, {
  required String prefix,
}) {
  return WorkbenchLaunchContext(
    sourceLabel: _joinContextParts([prefix, action.chainLabel]),
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

String buildWorkbenchSourceLabel(
  WorkbenchLaunchContext context, {
  required String prefix,
  bool includeWorkspaceBrief = true,
}) {
  return _joinContextParts([
    prefix,
    context.workspaceTargetLabel,
    context.cardTargetLabel,
    context.incidentTargetLabel,
    if (includeWorkspaceBrief) context.workspaceBrief,
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

int compareSectionKeysByDutyFocus(
  String a,
  String b,
  DutySummary? summary,
  Map<String, List<String>> focusOrder,
) {
  final aPriority = sectionPriorityForDutyFocus(a, summary, focusOrder);
  final bPriority = sectionPriorityForDutyFocus(b, summary, focusOrder);
  return aPriority.compareTo(bPriority);
}

int sectionPriorityForDutyFocus(
  String key,
  DutySummary? summary,
  Map<String, List<String>> focusOrder,
) {
  final focusWorkspace = summary?.focusWorkspaceTarget;
  final order = focusWorkspace == null ? null : focusOrder[focusWorkspace];
  if (order == null || order.isEmpty) {
    return 1 << 20;
  }
  final index = order.indexOf(key);
  return index == -1 ? 1 << 20 : index;
}

bool isDutyFocusSection(
  String key,
  DutySummary? summary,
  Map<String, List<String>> focusOrder,
) {
  return sectionPriorityForDutyFocus(key, summary, focusOrder) == 0;
}

String _joinContextParts(List<String?> parts) {
  final filtered = parts
      .whereType<String>()
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
  return filtered.join(' · ');
}

String? _workspaceTargetLabel(String target) {
  return {
    'audit_center': '历史与审计',
    'data_job_center': '分析任务中心',
    'data_governance': '资产治理板',
    'data_handoff': '分析交接板',
    'ai_runtime': 'AI 运行控制区',
    'ai_assets': 'AI 资产治理区',
    'optimization_job_center': '优化任务中心',
    'optimization_registry': '优化注册表',
    'optimization_operations': '优化运维板',
    'workspace': '工作台',
  }[target];
}

String? _cardTargetLabel(String target) {
  return {
    'strategy': '执行策略',
    'job_health': '任务健康',
    'asset_route': '资产路线',
    'asset_quality': '资产质量',
    'schema_topology': 'Schema 拓扑',
    'field_distribution': '字段分布',
    'risk_digest': '风险摘要',
    'next_actions': '下一步动作',
    'current_asset': '当前资产',
    'reference_asset': '基线资产',
    'drift_report': '漂移报告',
    'governance_decision': '治理结论',
    'runtime_product': '运行产物',
    'version_timeline': '版本轨迹',
    'registry_snapshot': '注册表快照',
    'solver_health': '求解器健康',
    'constraint_pressure': '约束压力',
    'explainability_probe': '解释性前哨',
    'recent_artifact': '最近产物',
    'registry_summary': '注册表摘要',
    'latest_snapshot': '最新快照',
    'summary': '当前卡片',
  }[target];
}

String? _incidentTargetLabel(String target) {
  return {
    'asset': '资产',
    'runtime': '运行态',
    'failure': '故障链路',
    'focus': '当前焦点',
    'summary': '摘要',
  }[target];
}
