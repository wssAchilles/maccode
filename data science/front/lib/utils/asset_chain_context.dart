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

  final cardLabel = _resolvedCardLabel(
    cardTarget: chain.cardTarget,
    cardTargetLabel: chain.cardTargetLabel,
  );
  final incidentLabel = _resolvedIncidentLabel(
    incidentTarget: chain.incidentTarget,
    incidentTargetLabel: chain.incidentTargetLabel,
  );

  return _joinContextParts([
    prefix,
    if (includeChainLabel) chain.label,
    if (includeWorkspace) chain.workspaceTargetLabel,
    if (includeCardTarget) cardLabel,
    if (includeIncident) incidentLabel,
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

String buildChainActionFeedbackMessage(
  AssetChainSummary? chain, {
  required String prefix,
  String? detail,
  bool includeChainLabel = false,
}) {
  if (chain == null) {
    return prefix;
  }
  return _joinContextParts([
    prefix,
    if (includeChainLabel) chain.label,
    chain.workspaceTargetLabel,
    _resolvedCardLabel(
      cardTarget: chain.cardTarget,
      cardTargetLabel: chain.cardTargetLabel,
    ),
    detail,
  ]);
}

String buildChainWorkspaceSummary(
  AssetChainSummary? chain, {
  bool includeWorkspaceLabel = false,
  String fallback = '--',
}) {
  if (chain == null) {
    return fallback;
  }

  final cleanedSummary = _cleanWorkspaceBrief(chain);
  final resolvedSummary = cleanedSummary.isNotEmpty
      ? cleanedSummary
      : _defaultWorkspaceSummary(chain);
  if (includeWorkspaceLabel) {
    return _joinContextParts([chain.workspaceTargetLabel, resolvedSummary]);
  }
  return resolvedSummary;
}

String? buildDutyContextCardValue(String? value) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty) {
    return null;
  }
  if (_isGenericDutyCardLabel(normalized)) {
    return null;
  }
  return normalized;
}

String? buildDutyContextIncidentValue(String? value) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty) {
    return null;
  }
  if (_isGenericDutyIncidentLabel(normalized)) {
    return null;
  }
  return normalized;
}

String? sanitizeWorkspaceSummaryText(
  String? summary, {
  Iterable<String?> duplicatedLabels = const [],
}) {
  final normalized = summary?.trim();
  if (normalized == null || normalized.isEmpty) {
    return null;
  }
  final cleaned = _cleanWorkspaceBriefParts(
    workspaceBrief: normalized,
    duplicatedLabels: duplicatedLabels,
  );
  if (cleaned.isEmpty) {
    return null;
  }
  return cleaned;
}

String buildWorkspaceSummaryText({
  required String workspaceTarget,
  required String workspaceTargetLabel,
  required String workspaceBrief,
  String? incidentBrief,
  String? cardTargetLabel,
  String? incidentTargetLabel,
  String? sectionTargetLabel,
  String? focusTargetLabel,
  bool includeWorkspaceLabel = false,
  String fallback = '--',
}) {
  final cardLabel = _resolvedCardLabel(
    cardTarget: '',
    cardTargetLabel: cardTargetLabel,
  );
  final incidentLabel = _resolvedIncidentLabel(
    incidentTarget: '',
    incidentTargetLabel: incidentTargetLabel,
  );
  final cleanedSummary = _cleanWorkspaceBriefParts(
    workspaceBrief: workspaceBrief,
    duplicatedLabels: [
      workspaceTargetLabel,
      cardLabel,
      incidentLabel,
      sectionTargetLabel,
      focusTargetLabel,
    ],
  );
  final resolvedSummary = cleanedSummary.isNotEmpty
      ? cleanedSummary
      : _defaultWorkspaceSummaryForTarget(
          workspaceTarget,
          incidentBrief: incidentBrief,
        );
  if (resolvedSummary.isEmpty) {
    return fallback;
  }
  if (includeWorkspaceLabel) {
    return _joinContextParts([workspaceTargetLabel, resolvedSummary]);
  }
  return resolvedSummary;
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
    _resolvedCardLabel(
      cardTarget: action.cardTarget,
      cardTargetLabel: action.cardTargetLabel,
    ),
    _resolvedIncidentLabel(
      incidentTarget: action.incidentTarget,
      incidentTargetLabel: action.incidentTargetLabel,
    ),
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
  final fallback = _dutyActionFallback(action.chainKey);
  final workspaceTarget = fallback?.workspaceTarget ?? action.workspaceTarget;
  final cardTarget = fallback?.cardTarget ?? action.cardTarget;
  final incidentTarget = fallback?.incidentTarget ?? action.incidentTarget;
  final workspaceBrief = fallback?.workspaceBrief ?? action.workspaceBrief;
  return WorkbenchLaunchContext(
    sourceLabel: _joinContextParts([prefix, action.label]),
    workspaceTarget: workspaceTarget,
    workspaceTargetLabel:
        _workspaceTargetLabel(workspaceTarget) ?? action.workspaceTargetLabel,
    cardTarget: cardTarget,
    cardTargetLabel: _cardTargetLabel(cardTarget) ?? action.cardTargetLabel,
    incidentTarget: incidentTarget,
    incidentTargetLabel:
        _incidentTargetLabel(incidentTarget) ?? action.incidentTargetLabel,
    workspaceBrief: workspaceBrief,
    watchSummary: _joinContextParts([
      _incidentTargetLabel(incidentTarget) ?? action.incidentTargetLabel,
      workspaceBrief,
    ]),
  );
}

String buildLaunchArrivalMessage(
  WorkbenchLaunchContext? context, {
  required String fallbackSubject,
  required String destination,
  String verb = '已打开',
  bool includeWorkspaceBrief = true,
}) {
  final subject = _compactLaunchSubject(
    _normalizeLaunchSubject(
      (context?.sourceLabel ?? fallbackSubject).trim(),
      context,
    ),
    context,
  );
  final actionText = verb == '已打开' && subject.contains(destination)
      ? subject
      : _joinLaunchPhrase(subject, verb, destination);
  if (context == null) {
    return actionText;
  }
  final cardLabel = _resolvedCardLabel(
    cardTarget: context.cardTarget,
    cardTargetLabel: context.cardTargetLabel,
  );
  final incidentLabel = _resolvedIncidentLabel(
    incidentTarget: context.incidentTarget,
    incidentTargetLabel: context.incidentTargetLabel,
  );
  final workspaceSummary = includeWorkspaceBrief
      ? sanitizeWorkspaceSummaryText(
          context.workspaceBrief,
          duplicatedLabels: [
            context.workspaceTargetLabel,
            cardLabel,
            incidentLabel,
          ],
        )
      : null;
  return _joinContextParts([
    actionText,
    context.workspaceTargetLabel,
    cardLabel,
    if (includeWorkspaceBrief) workspaceSummary,
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
    _resolvedCardLabel(
      cardTarget: context.cardTarget,
      cardTargetLabel: context.cardTargetLabel,
    ),
    _resolvedIncidentLabel(
      incidentTarget: context.incidentTarget,
      incidentTargetLabel: context.incidentTargetLabel,
    ),
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

String buildIncidentWatchValue(
  String? incidentLabel,
  String? watchSummary, {
  String fallback = '--',
}) {
  final segments = <String>[];
  void addSegment(String? value) {
    if (value == null) {
      return;
    }
    for (final part in value.split('·')) {
      final normalized = part.trim();
      if (normalized.isEmpty || segments.contains(normalized)) {
        continue;
      }
      segments.add(normalized);
    }
  }

  addSegment(incidentLabel);
  addSegment(watchSummary);
  if (segments.isEmpty) {
    return fallback;
  }
  return segments.join(' · ');
}

WorkbenchLaunchContext? normalizeLaunchContextSubject(
  WorkbenchLaunchContext? context, {
  required String fallbackSubject,
}) {
  if (context == null) {
    return null;
  }
  final normalized = _normalizeLaunchSubject(fallbackSubject, context);
  if (normalized == context.sourceLabel) {
    return context;
  }
  return WorkbenchLaunchContext(
    sourceLabel: normalized,
    workspaceTarget: context.workspaceTarget,
    workspaceTargetLabel: context.workspaceTargetLabel,
    cardTarget: context.cardTarget,
    cardTargetLabel: context.cardTargetLabel,
    incidentTarget: context.incidentTarget,
    incidentTargetLabel: context.incidentTargetLabel,
    workspaceBrief: context.workspaceBrief,
    watchSummary: context.watchSummary,
  );
}

String _joinLaunchPhrase(String subject, String verb, String destination) {
  final normalizedSubject = subject.trim();
  final normalizedDestination = destination.trim();
  final needsSpacer =
      normalizedSubject.isNotEmpty &&
      normalizedDestination.isNotEmpty &&
      RegExp(r'[A-Za-z]').hasMatch(normalizedDestination[0]) &&
      RegExp(r'[一-龥]$').hasMatch(normalizedSubject);
  final spacer = needsSpacer ? ' ' : '';
  return '$normalizedSubject$verb$spacer$normalizedDestination';
}

String _compactLaunchSubject(String subject, WorkbenchLaunchContext? context) {
  if (context == null || !subject.contains('·')) {
    return subject.trim();
  }
  final removableParts = <String>{};
  void addRemovablePart(String? value) {
    if (value == null) {
      return;
    }
    for (final part in value.split('·')) {
      final normalized = part.trim();
      if (normalized.isNotEmpty) {
        removableParts.add(normalized);
      }
    }
  }

  addRemovablePart(context.workspaceTargetLabel);
  addRemovablePart(context.cardTargetLabel);
  addRemovablePart(context.incidentTargetLabel);
  addRemovablePart(context.workspaceBrief);
  if (removableParts.isEmpty) {
    return subject.trim();
  }
  final subjectParts = subject
      .split('·')
      .map((part) => part.trim())
      .where((part) => part.isNotEmpty)
      .toList(growable: false);
  if (subjectParts.length <= 1) {
    return subject.trim();
  }
  final compactParts = <String>[subjectParts.first];
  for (final part in subjectParts.skip(1)) {
    if (!removableParts.contains(part)) {
      compactParts.add(part);
    }
  }
  return compactParts.join(' · ');
}

String _cleanWorkspaceBrief(AssetChainSummary chain) {
  return _cleanWorkspaceBriefParts(
    workspaceBrief: chain.workspaceBrief,
    duplicatedLabels: [
      chain.workspaceTargetLabel,
      chain.cardTargetLabel,
      chain.incidentTargetLabel,
      chain.sectionTargetLabel,
      chain.focusTargetLabel,
    ],
  );
}

String _cleanWorkspaceBriefParts({
  required String workspaceBrief,
  required Iterable<String?> duplicatedLabels,
}) {
  final parts = workspaceBrief
      .split('·')
      .map((part) => part.trim())
      .where((part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return '';
  }

  final labels = duplicatedLabels.whereType<String>().toSet();
  final cleanedParts = parts
      .where((part) => !_isMachineWorkspaceBriefPart(part, labels))
      .map(_normalizeWorkspaceBriefPart)
      .toList(growable: false);
  return cleanedParts.join(' · ');
}

String _normalizeWorkspaceBriefPart(String part) {
  final trimmed = part.trim();
  if (trimmed.isEmpty) {
    return trimmed;
  }

  final lower = trimmed.toLowerCase();
  if (lower == 'current watch') {
    return '当前关注';
  }
  if (lower == 'section target') {
    return '落点区域';
  }
  if (lower == 'duty focus') {
    return '值班焦点';
  }
  if (lower == 'sla watch') {
    return 'SLA 关注';
  }

  final overdue = RegExp(r'^overdue\s+(.+)$', caseSensitive: false).firstMatch(trimmed);
  if (overdue != null) {
    return '超时 ${overdue.group(1)!}';
  }
  final elapsed = RegExp(r'^elapsed\s+(.+)$', caseSensitive: false).firstMatch(trimmed);
  if (elapsed != null) {
    return '已运行 ${elapsed.group(1)!}';
  }
  final due = RegExp(r'^due\s+(.+)$', caseSensitive: false).firstMatch(trimmed);
  if (due != null) {
    return '截止 ${due.group(1)!}';
  }
  return trimmed;
}

bool _isMachineWorkspaceBriefPart(String part, Set<String> duplicatedLabels) {
  final lower = part.toLowerCase();
  if (duplicatedLabels.contains(part)) {
    return true;
  }
  if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(part)) {
    return true;
  }
  if (RegExp(r'^\d{2}-\d{2}\s+\d{2}:\d{2}$').hasMatch(part)) {
    return true;
  }
  if (RegExp(r'^\d+%$').hasMatch(part)) {
    return true;
  }
  if (RegExp(r'^\d+/\d+$').hasMatch(part)) {
    return true;
  }
  if ({
    'queued',
    'running',
    'started',
    'completed',
    'succeeded',
    'failed',
    'healthy',
    'idle',
    'ready',
    'watch',
    'incident',
    'active',
    'warning',
    'success',
    'job completed',
  }.contains(lower)) {
    return true;
  }
  if ({
    '已完成',
    '运行中',
    '已排队',
    '处理中',
    '链路健康',
    '需要关注',
    '故障待处置',
    '当前焦点',
    '当前卡片',
    '值班时限',
    '活跃作业',
    '运行控制区',
  }.contains(part)) {
    return true;
  }
  return false;
}

bool _isGenericDutyCardLabel(String label) {
  return {
    '当前卡片',
    '摘要卡',
    'summary',
  }.contains(label);
}

bool _isGenericDutyIncidentLabel(String label) {
  return {
    '值班时限',
    '当前焦点',
    'focus',
  }.contains(label);
}

String? _resolvedCardLabel({
  required String cardTarget,
  required String? cardTargetLabel,
}) {
  return buildDutyContextCardValue(
    _cardTargetLabel(cardTarget) ?? cardTargetLabel,
  );
}

String? _resolvedIncidentLabel({
  required String incidentTarget,
  required String? incidentTargetLabel,
}) {
  return buildDutyContextIncidentValue(
    _incidentTargetLabel(incidentTarget) ?? incidentTargetLabel,
  );
}

String _defaultWorkspaceSummaryForTarget(
  String workspaceTarget, {
  String? incidentBrief,
}) {
  switch (workspaceTarget) {
    case 'data_analysis_operations':
      return '上传 CSV、审查质量并启动分析任务。';
    case 'data_job_center':
      return '优先跟进分析任务、进度和失败重试。';
    case 'data_governance':
      return '优先核对当前资产、质量和治理结论。';
    case 'data_handoff':
      return '优先查看结果摘要并决定后续交接。';
    case 'ai_runtime':
      return '优先跟进 AI 运行队列、产物与资产状态。';
    case 'ai_assets':
      return '优先核对 AI 版本、注册表和回填入口。';
    case 'optimization_job_center':
      return '优先跟进后台优化任务和求解进度。';
    case 'optimization_registry':
      return '优先核对最新快照与结果摘要。';
    case 'optimization_operations':
      return '优先确认求解器健康、约束压力和解释性摘要。';
    case 'audit_center':
      return '优先查看统一事件流、资产矩阵和处置 Runbook。';
    default:
      return incidentBrief ?? '--';
  }
}

String _defaultWorkspaceSummary(AssetChainSummary chain) {
  switch (chain.workspaceTarget) {
    case 'data_analysis_operations':
      return '上传 CSV、审查质量并启动分析任务。';
    case 'data_job_center':
      return '优先跟进分析任务、进度和失败重试。';
    case 'data_governance':
      return '优先核对当前资产、质量和治理结论。';
    case 'data_handoff':
      return '优先查看结果摘要并决定后续交接。';
    case 'ai_runtime':
      return chain.key == 'knowledge'
          ? '优先跟进知识构建、快照与问答治理。'
          : '优先跟进训练队列、产物与模型资产。';
    case 'ai_assets':
      return chain.key == 'knowledge'
          ? '优先核对知识快照、集合和回填入口。'
          : '优先核对模型版本、注册表和回填入口。';
    case 'optimization_job_center':
      return '优先跟进后台优化任务和求解进度。';
    case 'optimization_registry':
      return '优先核对最新快照与结果摘要。';
    case 'optimization_operations':
      return '优先确认求解器健康、约束压力和解释性摘要。';
    case 'audit_center':
      return '优先查看统一事件流、资产矩阵和处置 Runbook。';
    default:
      return chain.incidentBrief;
  }
}

String _normalizeLaunchSubject(
  String subject,
  WorkbenchLaunchContext? context,
) {
  if (context == null || !subject.startsWith('Duty Actions')) {
    return subject;
  }
  final explicitDutyLabels = [
    '打开 AI Lab',
    '上传并分析数据',
    '运行能源优化',
    '开始模型训练',
    '构建知识库',
    '查看历史与审计',
  ];
  if (explicitDutyLabels.any(subject.contains)) {
    return subject.trim();
  }
  if (context.workspaceTarget == 'data_analysis_operations') {
    return 'Duty Actions · 上传并分析数据';
  }
  if (context.workspaceTarget == 'optimization_operations') {
    return 'Duty Actions · 运行能源优化';
  }
  if (context.workspaceTarget == 'ai_runtime' &&
      context.cardTarget == 'runtime_product') {
    if (context.workspaceBrief.contains('知识')) {
      return 'Duty Actions · 构建知识库';
    }
    return 'Duty Actions · 开始模型训练';
  }
  return subject;
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
    'data_analysis_operations': '分析执行区',
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

_DutyActionFallback? _dutyActionFallback(String chainKey) {
  return {
    'dataset': const _DutyActionFallback(
      workspaceTarget: 'data_analysis_operations',
      cardTarget: 'strategy',
      incidentTarget: 'asset',
      workspaceBrief: '数据分析工作台 · 上传 CSV、审查质量并启动分析任务。',
    ),
    'model': const _DutyActionFallback(
      workspaceTarget: 'ai_runtime',
      cardTarget: 'runtime_product',
      incidentTarget: 'runtime',
      workspaceBrief: 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
    ),
    'knowledge': const _DutyActionFallback(
      workspaceTarget: 'ai_runtime',
      cardTarget: 'runtime_product',
      incidentTarget: 'runtime',
      workspaceBrief: 'AI Lab 知识车道 · 提交构建任务并跟进知识快照、问答治理。',
    ),
    'optimization': const _DutyActionFallback(
      workspaceTarget: 'optimization_operations',
      cardTarget: 'solver_health',
      incidentTarget: 'asset',
      workspaceBrief: '优化工作台 · 运行优化任务并复核求解器、约束与结果摘要。',
    ),
  }[chainKey];
}

class _DutyActionFallback {
  const _DutyActionFallback({
    required this.workspaceTarget,
    required this.cardTarget,
    required this.incidentTarget,
    required this.workspaceBrief,
  });

  final String workspaceTarget;
  final String cardTarget;
  final String incidentTarget;
  final String workspaceBrief;
}
