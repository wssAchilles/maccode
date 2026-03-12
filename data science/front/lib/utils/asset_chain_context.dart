library;

import '../models/dashboard_summary.dart';

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
