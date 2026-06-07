/// 驾驶舱摘要模型
library;

import 'compute_rollout_policy.dart';
import 'job_record.dart';

class DashboardSummary {
  const DashboardSummary({
    required this.systemStatus,
    required this.kpis,
    this.dutySummary = const DutySummary.empty(),
    required this.recentJobs,
    required this.recentAssets,
    required this.recentHistory,
    required this.assetSummary,
    required this.alerts,
    this.controlPlane = const ControlPlaneStatus.empty(),
    this.computeAcceleration = const ComputeAccelerationStatus.empty(),
  });

  final List<SystemStatusItem> systemStatus;
  final DashboardKpis kpis;
  final DutySummary dutySummary;
  final List<JobRecord> recentJobs;
  final List<DatasetAsset> recentAssets;
  final List<AuditActivity> recentHistory;
  final AssetSummary assetSummary;
  final List<DashboardAlert> alerts;
  final ControlPlaneStatus controlPlane;
  final ComputeAccelerationStatus computeAcceleration;

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      systemStatus: _mapList(json['system_status'], SystemStatusItem.fromJson),
      kpis: DashboardKpis.fromJson(
        json['kpis'] is Map
            ? Map<String, dynamic>.from(json['kpis'] as Map)
            : const {},
      ),
      dutySummary: DutySummary.fromJson(
        json['duty_summary'] is Map
            ? Map<String, dynamic>.from(json['duty_summary'] as Map)
            : const {},
      ),
      recentJobs: _mapList(json['recent_jobs'], JobRecord.fromJson),
      recentAssets: _mapList(json['recent_assets'], DatasetAsset.fromJson),
      recentHistory: _mapList(json['recent_history'], AuditActivity.fromJson),
      assetSummary: AssetSummary.fromJson(
        json['asset_summary'] is Map
            ? Map<String, dynamic>.from(json['asset_summary'] as Map)
            : const {},
      ),
      alerts: _mapList(json['alerts'], DashboardAlert.fromJson),
      controlPlane: ControlPlaneStatus.fromJson(
        json['control_plane'] is Map
            ? Map<String, dynamic>.from(json['control_plane'] as Map)
            : const {},
      ),
      computeAcceleration: ComputeAccelerationStatus.fromJson(
        json['compute_acceleration'] is Map
            ? Map<String, dynamic>.from(json['compute_acceleration'] as Map)
            : const {},
      ),
    );
  }
}

class ControlPlaneStatus {
  const ControlPlaneStatus({
    required this.enabled,
    required this.executionMode,
    required this.orchestratorUrl,
    required this.status,
    required this.message,
    required this.dispatchTimeoutS,
    required this.activeOperations,
    required this.pythonWorkerConfigured,
    this.lightLane = const ControlPlaneLane.empty(),
    this.heavyLane = const ControlPlaneLane.empty(),
    this.computeAcceleration = const ComputeAccelerationStatus.empty(),
    this.computeRollout = const ComputeRolloutPolicy.empty(),
  });

  const ControlPlaneStatus.empty()
    : enabled = false,
      executionMode = '',
      orchestratorUrl = '',
      status = 'info',
      message = '',
      dispatchTimeoutS = 0,
      activeOperations = 0,
      pythonWorkerConfigured = false,
      lightLane = const ControlPlaneLane.empty(),
      heavyLane = const ControlPlaneLane.empty(),
      computeAcceleration = const ComputeAccelerationStatus.empty(),
      computeRollout = const ComputeRolloutPolicy.empty();

  final bool enabled;
  final String executionMode;
  final String orchestratorUrl;
  final String status;
  final String message;
  final int dispatchTimeoutS;
  final int activeOperations;
  final bool pythonWorkerConfigured;
  final ControlPlaneLane lightLane;
  final ControlPlaneLane heavyLane;
  final ComputeAccelerationStatus computeAcceleration;
  final ComputeRolloutPolicy computeRollout;

  factory ControlPlaneStatus.fromJson(Map<String, dynamic> json) {
    return ControlPlaneStatus(
      enabled: _asBool(json['enabled']) ?? false,
      executionMode: (json['execution_mode'] ?? '').toString(),
      orchestratorUrl: (json['orchestrator_url'] ?? '').toString(),
      status: (json['status'] ?? 'info').toString(),
      message: (json['message'] ?? '').toString(),
      dispatchTimeoutS: _asInt(json['dispatch_timeout_s']) ?? 0,
      activeOperations: _asInt(json['active_operations']) ?? 0,
      pythonWorkerConfigured:
          _asBool(json['python_worker_configured']) ?? false,
      lightLane: ControlPlaneLane.fromJson(
        json['light_lane'] is Map
            ? Map<String, dynamic>.from(json['light_lane'] as Map)
            : const {},
      ),
      heavyLane: ControlPlaneLane.fromJson(
        json['heavy_lane'] is Map
            ? Map<String, dynamic>.from(json['heavy_lane'] as Map)
            : const {},
      ),
      computeAcceleration: ComputeAccelerationStatus.fromJson(
        json['compute_acceleration'] is Map
            ? Map<String, dynamic>.from(json['compute_acceleration'] as Map)
            : const {},
      ),
      computeRollout: ComputeRolloutPolicy.fromJson(
        json['compute_rollout'] is Map
            ? Map<String, dynamic>.from(json['compute_rollout'] as Map)
            : const {},
      ),
    );
  }
}

class ControlPlaneLane {
  const ControlPlaneLane({
    required this.capacity,
    required this.available,
    required this.inUse,
  });

  const ControlPlaneLane.empty() : capacity = 0, available = 0, inUse = 0;

  final int capacity;
  final int available;
  final int inUse;

  factory ControlPlaneLane.fromJson(Map<String, dynamic> json) {
    return ControlPlaneLane(
      capacity: _asInt(json['capacity']) ?? 0,
      available: _asInt(json['available']) ?? 0,
      inUse: _asInt(json['in_use']) ?? 0,
    );
  }
}

class ComputeAccelerationStatus {
  const ComputeAccelerationStatus({
    required this.enabled,
    required this.status,
    required this.message,
    required this.preferredBackend,
    required this.activeBackend,
    required this.nativeEnabled,
    required this.nativeAvailable,
    required this.profiledComponents,
    required this.benchmarkReady,
    required this.hottestComponent,
    required this.lastUpdatedAt,
    this.components = const [],
    this.rollout = const ComputeRolloutPolicy.empty(),
  });

  const ComputeAccelerationStatus.empty()
    : enabled = false,
      status = 'info',
      message = '',
      preferredBackend = 'python_pandas',
      activeBackend = 'python_pandas',
      nativeEnabled = false,
      nativeAvailable = false,
      profiledComponents = 0,
      benchmarkReady = false,
      hottestComponent = '--',
      lastUpdatedAt = '',
      components = const [],
      rollout = const ComputeRolloutPolicy.empty();

  final bool enabled;
  final String status;
  final String message;
  final String preferredBackend;
  final String activeBackend;
  final bool nativeEnabled;
  final bool nativeAvailable;
  final int profiledComponents;
  final bool benchmarkReady;
  final String hottestComponent;
  final String lastUpdatedAt;
  final List<ComputeAccelerationComponent> components;
  final ComputeRolloutPolicy rollout;

  factory ComputeAccelerationStatus.fromJson(Map<String, dynamic> json) {
    return ComputeAccelerationStatus(
      enabled: _asBool(json['enabled']) ?? false,
      status: (json['status'] ?? 'info').toString(),
      message: (json['message'] ?? '').toString(),
      preferredBackend: (json['preferred_backend'] ?? 'python_pandas')
          .toString(),
      activeBackend: (json['active_backend'] ?? 'python_pandas').toString(),
      nativeEnabled: _asBool(json['native_enabled']) ?? false,
      nativeAvailable: _asBool(json['native_available']) ?? false,
      profiledComponents: _asInt(json['profiled_components']) ?? 0,
      benchmarkReady: _asBool(json['benchmark_ready']) ?? false,
      hottestComponent: (json['hottest_component'] ?? '--').toString(),
      lastUpdatedAt: (json['last_updated_at'] ?? '').toString(),
      components: _mapList(
        json['components'],
        ComputeAccelerationComponent.fromJson,
      ),
      rollout: ComputeRolloutPolicy.fromJson(
        json['rollout'] is Map
            ? Map<String, dynamic>.from(json['rollout'] as Map)
            : const {},
      ),
    );
  }
}

class ComputeAccelerationComponent {
  const ComputeAccelerationComponent({
    required this.key,
    required this.label,
    required this.status,
    required this.activeBackend,
    required this.preferredBackend,
    required this.nativeEnabled,
    required this.nativeAvailable,
    required this.lastDurationMs,
    required this.avgDurationMs,
    required this.p95DurationMs,
    required this.invocationCount,
    required this.lastRows,
    required this.lastContext,
    required this.contexts,
    required this.recommendedAction,
  });

  final String key;
  final String label;
  final String status;
  final String activeBackend;
  final String preferredBackend;
  final bool nativeEnabled;
  final bool nativeAvailable;
  final double lastDurationMs;
  final double avgDurationMs;
  final double p95DurationMs;
  final int invocationCount;
  final int lastRows;
  final String lastContext;
  final List<String> contexts;
  final String recommendedAction;

  factory ComputeAccelerationComponent.fromJson(Map<String, dynamic> json) {
    return ComputeAccelerationComponent(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '--').toString(),
      status: (json['status'] ?? 'info').toString(),
      activeBackend: (json['active_backend'] ?? 'python_pandas').toString(),
      preferredBackend: (json['preferred_backend'] ?? 'python_pandas')
          .toString(),
      nativeEnabled: _asBool(json['native_enabled']) ?? false,
      nativeAvailable: _asBool(json['native_available']) ?? false,
      lastDurationMs: _asDouble(json['last_duration_ms']) ?? 0.0,
      avgDurationMs: _asDouble(json['avg_duration_ms']) ?? 0.0,
      p95DurationMs: _asDouble(json['p95_duration_ms']) ?? 0.0,
      invocationCount: _asInt(json['invocation_count']) ?? 0,
      lastRows: _asInt(json['last_rows']) ?? 0,
      lastContext: (json['last_context'] ?? '').toString(),
      contexts: _mapPrimitiveList(json['contexts']),
      recommendedAction: (json['recommended_action'] ?? '保持监控').toString(),
    );
  }
}

class DutySummary {
  const DutySummary({
    required this.incidentCount,
    required this.activeCount,
    required this.watchCount,
    required this.overdueCount,
    required this.escalatedCount,
    required this.alertCount,
    required this.degradedSystemCount,
    required this.focusChainKey,
    required this.focusChainLabel,
    required this.focusWorkspaceTarget,
    required this.focusWorkspaceTargetLabel,
    required this.focusCardTarget,
    required this.focusCardTargetLabel,
    required this.focusIncidentTarget,
    required this.focusIncidentTargetLabel,
    required this.focusWatch,
    required this.focusOwnerLabel,
    required this.focusEscalationStateLabel,
    this.overviewActions = const [],
    this.auditActions = const [],
  });

  const DutySummary.empty()
    : incidentCount = 0,
      activeCount = 0,
      watchCount = 0,
      overdueCount = 0,
      escalatedCount = 0,
      alertCount = 0,
      degradedSystemCount = 0,
      focusChainKey = '',
      focusChainLabel = '--',
      focusWorkspaceTarget = 'workspace',
      focusWorkspaceTargetLabel = '工作台',
      focusCardTarget = 'summary',
      focusCardTargetLabel = '当前卡片',
      focusIncidentTarget = 'focus',
      focusIncidentTargetLabel = '当前焦点',
      focusWatch = '当前暂无高优先级链路',
      focusOwnerLabel = '--',
      focusEscalationStateLabel = '--',
      overviewActions = const [],
      auditActions = const [];

  final int incidentCount;
  final int activeCount;
  final int watchCount;
  final int overdueCount;
  final int escalatedCount;
  final int alertCount;
  final int degradedSystemCount;
  final String focusChainKey;
  final String focusChainLabel;
  final String focusWorkspaceTarget;
  final String focusWorkspaceTargetLabel;
  final String focusCardTarget;
  final String focusCardTargetLabel;
  final String focusIncidentTarget;
  final String focusIncidentTargetLabel;
  final String focusWatch;
  final String focusOwnerLabel;
  final String focusEscalationStateLabel;
  final List<DutyAction> overviewActions;
  final List<DutyAction> auditActions;

  factory DutySummary.fromJson(Map<String, dynamic> json) {
    return DutySummary(
      incidentCount: _asInt(json['incident_count']) ?? 0,
      activeCount: _asInt(json['active_count']) ?? 0,
      watchCount: _asInt(json['watch_count']) ?? 0,
      overdueCount: _asInt(json['overdue_count']) ?? 0,
      escalatedCount: _asInt(json['escalated_count']) ?? 0,
      alertCount: _asInt(json['alert_count']) ?? 0,
      degradedSystemCount: _asInt(json['degraded_system_count']) ?? 0,
      focusChainKey: (json['focus_chain_key'] ?? '').toString(),
      focusChainLabel: (json['focus_chain_label'] ?? '--').toString(),
      focusWorkspaceTarget: (json['focus_workspace_target'] ?? 'workspace')
          .toString(),
      focusWorkspaceTargetLabel:
          (json['focus_workspace_target_label'] ??
                  _defaultWorkspaceTargetLabel(
                    (json['focus_workspace_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      focusCardTarget: (json['focus_card_target'] ?? 'summary').toString(),
      focusCardTargetLabel:
          (json['focus_card_target_label'] ??
                  _defaultCardTargetLabel(
                    (json['focus_card_target'] ?? 'summary').toString(),
                  ))
              .toString(),
      focusIncidentTarget: (json['focus_incident_target'] ?? 'focus')
          .toString(),
      focusIncidentTargetLabel:
          (json['focus_incident_target_label'] ??
                  _defaultIncidentTargetLabel(
                    (json['focus_incident_target'] ?? 'focus').toString(),
                  ))
              .toString(),
      focusWatch: (json['focus_watch'] ?? '当前暂无高优先级链路').toString(),
      focusOwnerLabel: (json['focus_owner_label'] ?? '--').toString(),
      focusEscalationStateLabel: (json['focus_escalation_state_label'] ?? '--')
          .toString(),
      overviewActions: _mapList(json['overview_actions'], DutyAction.fromJson),
      auditActions: _mapList(json['audit_actions'], DutyAction.fromJson),
    );
  }
}

class DutyAction {
  const DutyAction({
    required this.command,
    required this.label,
    required this.tone,
    required this.chainKey,
    required this.chainLabel,
    required this.workspaceTarget,
    required this.workspaceTargetLabel,
    required this.cardTarget,
    required this.cardTargetLabel,
    required this.incidentTarget,
    required this.incidentTargetLabel,
    required this.workspaceBrief,
  });

  final String command;
  final String label;
  final String tone;
  final String chainKey;
  final String chainLabel;
  final String workspaceTarget;
  final String workspaceTargetLabel;
  final String cardTarget;
  final String cardTargetLabel;
  final String incidentTarget;
  final String incidentTargetLabel;
  final String workspaceBrief;

  factory DutyAction.fromJson(Map<String, dynamic> json) {
    final workspaceTarget = (json['workspace_target'] ?? 'workspace')
        .toString();
    final cardTarget = (json['card_target'] ?? 'summary').toString();
    final incidentTarget = (json['incident_target'] ?? 'focus').toString();
    return DutyAction(
      command: (json['command'] ?? 'open_workspace').toString(),
      label: (json['label'] ?? '打开工作台').toString(),
      tone: (json['tone'] ?? 'outline').toString(),
      chainKey: (json['chain_key'] ?? '').toString(),
      chainLabel: (json['chain_label'] ?? '--').toString(),
      workspaceTarget: workspaceTarget,
      workspaceTargetLabel:
          (json['workspace_target_label'] ??
                  _defaultWorkspaceTargetLabel(workspaceTarget))
              .toString(),
      cardTarget: cardTarget,
      cardTargetLabel:
          (json['card_target_label'] ?? _defaultCardTargetLabel(cardTarget))
              .toString(),
      incidentTarget: incidentTarget,
      incidentTargetLabel:
          (json['incident_target_label'] ??
                  _defaultIncidentTargetLabel(incidentTarget))
              .toString(),
      workspaceBrief: (json['workspace_brief'] ?? '--').toString(),
    );
  }
}

class AssetSummary {
  const AssetSummary({
    required this.inventory,
    required this.datasets,
    required this.models,
    required this.knowledgeBases,
    required this.optimizations,
    required this.failureChains,
    required this.governance,
    required this.chainSummaries,
  });

  final AssetInventory inventory;
  final List<AssetDataset> datasets;
  final List<AssetModel> models;
  final List<KnowledgeAsset> knowledgeBases;
  final List<OptimizationAsset> optimizations;
  final List<AssetFailureChain> failureChains;
  final List<AssetGovernanceItem> governance;
  final List<AssetChainSummary> chainSummaries;

  factory AssetSummary.fromJson(Map<String, dynamic> json) {
    return AssetSummary(
      inventory: AssetInventory.fromJson(
        json['inventory'] is Map
            ? Map<String, dynamic>.from(json['inventory'] as Map)
            : const {},
      ),
      datasets: _mapList(json['datasets'], AssetDataset.fromJson),
      models: _mapList(json['models'], AssetModel.fromJson),
      knowledgeBases: _mapList(
        json['knowledge_bases'],
        KnowledgeAsset.fromJson,
      ),
      optimizations: _mapList(
        json['optimizations'],
        OptimizationAsset.fromJson,
      ),
      failureChains: _mapList(
        json['failure_chains'],
        AssetFailureChain.fromJson,
      ),
      governance: _mapList(json['governance'], AssetGovernanceItem.fromJson),
      chainSummaries: _mapList(
        json['chain_summaries'],
        AssetChainSummary.fromJson,
      ),
    );
  }
}

class AssetChainSummary {
  const AssetChainSummary({
    required this.key,
    required this.label,
    required this.status,
    required this.statusLabel,
    required this.priorityScore,
    required this.ownerLabel,
    required this.slaMinutes,
    required this.escalationLabel,
    this.slaDeadlineAt,
    required this.elapsedMinutes,
    required this.overdueMinutes,
    required this.isOverdue,
    required this.escalationTier,
    required this.escalationStateLabel,
    required this.latestVersion,
    required this.latestLabel,
    required this.lineageSummary,
    required this.failureSummary,
    required this.focusLabel,
    required this.focusDetail,
    required this.focusTarget,
    required this.focusTargetLabel,
    required this.sectionTarget,
    required this.sectionTargetLabel,
    required this.workspaceTarget,
    required this.workspaceTargetLabel,
    required this.workspaceBrief,
    required this.cardTarget,
    required this.cardTargetLabel,
    required this.incidentTarget,
    required this.incidentTargetLabel,
    required this.incidentBrief,
    required this.narrativeTarget,
    required this.narrativeTargetLabel,
    required this.dispositionTarget,
    required this.dispositionTargetLabel,
    required this.runbookTitle,
    required this.runbookSteps,
    required this.activityTitle,
    required this.activityStatus,
    required this.activitySource,
    required this.failurePhase,
    required this.failureSource,
    required this.jobStatus,
    required this.jobProgress,
    required this.jobPhase,
    required this.actionLabel,
    required this.timeline,
    this.activityAt,
    this.failureJobId,
  });

  final String key;
  final String label;
  final String status;
  final String statusLabel;
  final int priorityScore;
  final String ownerLabel;
  final int slaMinutes;
  final String escalationLabel;
  final DateTime? slaDeadlineAt;
  final int elapsedMinutes;
  final int overdueMinutes;
  final bool isOverdue;
  final int escalationTier;
  final String escalationStateLabel;
  final String latestVersion;
  final String latestLabel;
  final String lineageSummary;
  final String failureSummary;
  final String focusLabel;
  final String focusDetail;
  final String focusTarget;
  final String focusTargetLabel;
  final String sectionTarget;
  final String sectionTargetLabel;
  final String workspaceTarget;
  final String workspaceTargetLabel;
  final String workspaceBrief;
  final String cardTarget;
  final String cardTargetLabel;
  final String incidentTarget;
  final String incidentTargetLabel;
  final String incidentBrief;
  final String narrativeTarget;
  final String narrativeTargetLabel;
  final String dispositionTarget;
  final String dispositionTargetLabel;
  final String runbookTitle;
  final List<String> runbookSteps;
  final String activityTitle;
  final String activityStatus;
  final String activitySource;
  final DateTime? activityAt;
  final String? failureJobId;
  final String failurePhase;
  final String failureSource;
  final String jobStatus;
  final int jobProgress;
  final String jobPhase;
  final String actionLabel;
  final List<AssetChainNode> timeline;

  factory AssetChainSummary.fromJson(Map<String, dynamic> json) {
    return AssetChainSummary(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      status: (json['status'] ?? 'healthy').toString(),
      statusLabel: (json['status_label'] ?? '链路健康').toString(),
      priorityScore: _asInt(json['priority_score']) ?? 0,
      ownerLabel: (json['owner_label'] ?? '--').toString(),
      slaMinutes: _asInt(json['sla_minutes']) ?? 0,
      escalationLabel: (json['escalation_label'] ?? '--').toString(),
      slaDeadlineAt: _parseDateTime(json['sla_deadline_at']),
      elapsedMinutes: _asInt(json['elapsed_minutes']) ?? 0,
      overdueMinutes: _asInt(json['overdue_minutes']) ?? 0,
      isOverdue: _asBool(json['is_overdue']) ?? false,
      escalationTier: _asInt(json['escalation_tier']) ?? 0,
      escalationStateLabel: (json['escalation_state_label'] ?? '--').toString(),
      latestVersion: (json['latest_version'] ?? '--').toString(),
      latestLabel: (json['latest_label'] ?? '--').toString(),
      lineageSummary: (json['lineage_summary'] ?? '--').toString(),
      failureSummary: (json['failure_summary'] ?? '--').toString(),
      focusLabel: (json['focus_label'] ?? '--').toString(),
      focusDetail: (json['focus_detail'] ?? '--').toString(),
      focusTarget: (json['focus_target'] ?? 'workspace').toString(),
      focusTargetLabel:
          (json['focus_target_label'] ??
                  _defaultFocusTargetLabel(
                    (json['focus_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      sectionTarget: (json['section_target'] ?? 'workspace').toString(),
      sectionTargetLabel:
          (json['section_target_label'] ??
                  _defaultSectionTargetLabel(
                    (json['section_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      workspaceTarget: (json['workspace_target'] ?? 'workspace').toString(),
      workspaceTargetLabel:
          (json['workspace_target_label'] ??
                  _defaultWorkspaceTargetLabel(
                    (json['workspace_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      workspaceBrief: (json['workspace_brief'] ?? '--').toString(),
      cardTarget: (json['card_target'] ?? 'summary').toString(),
      cardTargetLabel:
          (json['card_target_label'] ??
                  _defaultCardTargetLabel(
                    (json['card_target'] ?? 'summary').toString(),
                  ))
              .toString(),
      incidentTarget: (json['incident_target'] ?? 'focus').toString(),
      incidentTargetLabel:
          (json['incident_target_label'] ??
                  _defaultIncidentTargetLabel(
                    (json['incident_target'] ?? 'focus').toString(),
                  ))
              .toString(),
      incidentBrief: (json['incident_brief'] ?? '--').toString(),
      narrativeTarget: (json['narrative_target'] ?? 'target').toString(),
      narrativeTargetLabel:
          (json['narrative_target_label'] ??
                  _defaultNarrativeTargetLabel(
                    (json['narrative_target'] ?? 'target').toString(),
                  ))
              .toString(),
      dispositionTarget: (json['disposition_target'] ?? 'focus').toString(),
      dispositionTargetLabel:
          (json['disposition_target_label'] ??
                  _defaultDispositionTargetLabel(
                    (json['disposition_target'] ?? 'focus').toString(),
                  ))
              .toString(),
      runbookTitle: (json['runbook_title'] ?? '处置 Runbook').toString(),
      runbookSteps: _mapPrimitiveList(json['runbook_steps']),
      activityTitle: (json['activity_title'] ?? '--').toString(),
      activityStatus: (json['activity_status'] ?? '--').toString(),
      activitySource: (json['activity_source'] ?? '--').toString(),
      activityAt: _parseDateTime(json['activity_at']),
      failureJobId: json['failure_job_id']?.toString(),
      failurePhase: (json['failure_phase'] ?? '--').toString(),
      failureSource: (json['failure_source'] ?? '--').toString(),
      jobStatus: (json['job_status'] ?? '--').toString(),
      jobProgress: _asInt(json['job_progress']) ?? 0,
      jobPhase: (json['job_phase'] ?? '--').toString(),
      actionLabel: (json['action_label'] ?? '打开工作台').toString(),
      timeline: _mapList(json['timeline'], AssetChainNode.fromJson),
    );
  }
}

String _defaultCardTargetLabel(String target) {
  switch (target) {
    case 'strategy':
      return '执行策略';
    case 'job_health':
      return '任务健康';
    case 'asset_route':
      return '资产路线';
    case 'asset_quality':
      return '资产质量';
    case 'schema_topology':
      return 'Schema 拓扑';
    case 'field_distribution':
      return '字段分布';
    case 'risk_digest':
      return '风险摘要';
    case 'next_actions':
      return '下一步动作';
    case 'current_asset':
      return '当前资产';
    case 'reference_asset':
      return '基线资产';
    case 'drift_report':
      return '漂移报告';
    case 'governance_decision':
      return '治理结论';
    case 'runtime_product':
      return '运行产物';
    case 'version_timeline':
      return '版本轨迹';
    case 'registry_snapshot':
      return '注册表快照';
    case 'solver_health':
      return '求解器健康';
    case 'constraint_pressure':
      return '约束压力';
    case 'explainability_probe':
      return '解释性前哨';
    case 'recent_artifact':
      return '最近产物';
    case 'registry_summary':
      return '注册表摘要';
    case 'latest_snapshot':
      return '最新快照';
    case 'summary':
    default:
      return '当前卡片';
  }
}

String _defaultWorkspaceTargetLabel(String target) {
  switch (target) {
    case 'audit_center':
      return '历史与审计';
    case 'data_job_center':
      return '分析任务中心';
    case 'data_governance':
      return '资产治理板';
    case 'data_handoff':
      return '分析交接板';
    case 'ai_runtime':
      return 'AI 运行控制区';
    case 'ai_assets':
      return 'AI 资产治理区';
    case 'optimization_job_center':
      return '优化任务中心';
    case 'optimization_registry':
      return '优化注册表';
    case 'optimization_operations':
      return '优化运维板';
    default:
      return '工作台';
  }
}

String _defaultIncidentTargetLabel(String target) {
  switch (target) {
    case 'sla':
      return '值班时限';
    case 'failure':
      return '失败链路';
    case 'runtime':
      return '活跃作业';
    case 'asset':
      return '资产状态';
    case 'activity':
      return '最近活动';
    default:
      return '当前焦点';
  }
}

String _defaultFocusTargetLabel(String target) {
  switch (target) {
    case 'dataset_current_asset':
      return '当前资产';
    case 'dataset_reference_asset':
      return '基线资产';
    case 'dataset_drift_report':
      return '漂移报告';
    case 'dataset_governance_decision':
      return '治理决策';
    case 'dataset_results':
      return '分析结果';
    case 'dataset_job_panel':
      return '数据任务';
    case 'model_runtime':
      return '训练运行态';
    case 'model_registry':
      return '模型注册表';
    case 'knowledge_runtime':
      return '知识运行态';
    case 'knowledge_registry':
      return '知识注册表';
    case 'optimization_solver':
      return '求解器运维';
    case 'optimization_constraint':
      return '约束压力';
    case 'optimization_explainability':
      return '解释性前哨';
    case 'optimization_registry':
      return '优化注册表';
    case 'optimization_job_panel':
      return '优化任务';
    default:
      return '工作台';
  }
}

String _defaultSectionTargetLabel(String target) {
  switch (target) {
    case 'data_analysis_operations':
      return '运营态工作台';
    case 'data_analysis_results':
      return '结果资产台';
    case 'ai_lab_runtime':
      return '运行控制区';
    case 'ai_lab_assets':
      return '资产治理区';
    case 'optimization_operations':
      return '优化运维区';
    case 'optimization_assets':
      return '资产注册表';
    default:
      return '工作台';
  }
}

String _defaultNarrativeTargetLabel(String target) {
  switch (target) {
    case 'lineage':
      return '版本血缘';
    case 'target':
      return '目标落点';
    case 'sla':
      return '响应时限';
    case 'activity':
      return '最近活动';
    case 'job':
      return '活跃作业';
    case 'action':
      return '当前处置';
    default:
      return '目标落点';
  }
}

String _defaultDispositionTargetLabel(String target) {
  switch (target) {
    case 'governance':
      return '风险建议';
    case 'focus':
      return '当前焦点';
    case 'sla':
      return '响应时限';
    case 'replay':
      return '回放库存';
    case 'failure':
      return '失败链路';
    case 'job':
      return '活跃作业';
    default:
      return '当前焦点';
  }
}

class AssetChainNode {
  const AssetChainNode({
    required this.kind,
    required this.title,
    required this.detail,
    required this.level,
    required this.badge,
    required this.sourceLabel,
    required this.versionTag,
    required this.phaseLabel,
    this.timestamp,
  });

  final String kind;
  final String title;
  final String detail;
  final String level;
  final String badge;
  final String sourceLabel;
  final String versionTag;
  final String phaseLabel;
  final DateTime? timestamp;

  factory AssetChainNode.fromJson(Map<String, dynamic> json) {
    return AssetChainNode(
      kind: (json['kind'] ?? 'info').toString(),
      title: (json['title'] ?? '--').toString(),
      detail: (json['detail'] ?? '--').toString(),
      level: (json['level'] ?? 'info').toString(),
      badge: (json['badge'] ?? '--').toString(),
      sourceLabel: (json['source_label'] ?? '--').toString(),
      versionTag: (json['version_tag'] ?? '--').toString(),
      phaseLabel: (json['phase_label'] ?? '--').toString(),
      timestamp: _parseDateTime(json['timestamp']),
    );
  }
}

class AssetFailureChain {
  const AssetFailureChain({
    required this.key,
    required this.jobType,
    required this.label,
    required this.jobId,
    required this.contextLabel,
    required this.latestPhase,
    required this.statusMessage,
    required this.errorCode,
    required this.errorMessage,
    required this.sourceSummary,
    required this.lineageSummary,
    required this.attemptCount,
    required this.maxAttempts,
    required this.latestVersion,
    required this.recommendedAction,
    required this.actionLabel,
    required this.workspaceTarget,
    required this.workspaceTargetLabel,
    required this.workspaceBrief,
    this.submittedAt,
    this.completedAt,
  });

  final String key;
  final String jobType;
  final String label;
  final String jobId;
  final String contextLabel;
  final String latestPhase;
  final String statusMessage;
  final String errorCode;
  final String errorMessage;
  final String sourceSummary;
  final String lineageSummary;
  final int attemptCount;
  final int maxAttempts;
  final String latestVersion;
  final String recommendedAction;
  final String actionLabel;
  final String workspaceTarget;
  final String workspaceTargetLabel;
  final String workspaceBrief;
  final DateTime? submittedAt;
  final DateTime? completedAt;

  factory AssetFailureChain.fromJson(Map<String, dynamic> json) {
    return AssetFailureChain(
      key: (json['key'] ?? '').toString(),
      jobType: (json['job_type'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      jobId: (json['job_id'] ?? '').toString(),
      contextLabel: (json['context_label'] ?? '--').toString(),
      latestPhase: (json['latest_phase'] ?? 'failed').toString(),
      statusMessage: (json['status_message'] ?? '').toString(),
      errorCode: (json['error_code'] ?? 'JOB_FAILED').toString(),
      errorMessage: (json['error_message'] ?? '').toString(),
      sourceSummary: (json['source_summary'] ?? '--').toString(),
      lineageSummary: (json['lineage_summary'] ?? '--').toString(),
      attemptCount: _asInt(json['attempt_count']) ?? 0,
      maxAttempts: _asInt(json['max_attempts']) ?? 1,
      latestVersion: (json['latest_version'] ?? '--').toString(),
      recommendedAction: (json['recommended_action'] ?? '').toString(),
      actionLabel: (json['action_label'] ?? '打开工作台').toString(),
      workspaceTarget: (json['workspace_target'] ?? 'workspace').toString(),
      workspaceTargetLabel:
          (json['workspace_target_label'] ??
                  _defaultWorkspaceTargetLabel(
                    (json['workspace_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      workspaceBrief: (json['workspace_brief'] ?? '--').toString(),
      submittedAt: _parseDateTime(json['submitted_at']),
      completedAt: _parseDateTime(json['completed_at']),
    );
  }
}

class AssetGovernanceItem {
  const AssetGovernanceItem({
    required this.key,
    required this.label,
    required this.riskLevel,
    required this.assetCount,
    required this.failedJobs,
    required this.ownerLabel,
    required this.slaMinutes,
    required this.escalationLabel,
    required this.latestVersion,
    required this.latestLabel,
    required this.lineageSummary,
    required this.failureSummary,
    required this.recommendedAction,
    required this.actionLabel,
    required this.workspaceTarget,
    required this.workspaceTargetLabel,
    required this.workspaceBrief,
  });

  final String key;
  final String label;
  final String riskLevel;
  final int assetCount;
  final int failedJobs;
  final String ownerLabel;
  final int slaMinutes;
  final String escalationLabel;
  final String latestVersion;
  final String latestLabel;
  final String lineageSummary;
  final String failureSummary;
  final String recommendedAction;
  final String actionLabel;
  final String workspaceTarget;
  final String workspaceTargetLabel;
  final String workspaceBrief;

  factory AssetGovernanceItem.fromJson(Map<String, dynamic> json) {
    return AssetGovernanceItem(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      riskLevel: (json['risk_level'] ?? 'healthy').toString(),
      assetCount: _asInt(json['asset_count']) ?? 0,
      failedJobs: _asInt(json['failed_jobs']) ?? 0,
      ownerLabel: (json['owner_label'] ?? '--').toString(),
      slaMinutes: _asInt(json['sla_minutes']) ?? 0,
      escalationLabel: (json['escalation_label'] ?? '--').toString(),
      latestVersion: (json['latest_version'] ?? '--').toString(),
      latestLabel: (json['latest_label'] ?? '--').toString(),
      lineageSummary: (json['lineage_summary'] ?? '--').toString(),
      failureSummary: (json['failure_summary'] ?? '--').toString(),
      recommendedAction: (json['recommended_action'] ?? '').toString(),
      actionLabel: (json['action_label'] ?? '打开工作台').toString(),
      workspaceTarget: (json['workspace_target'] ?? 'workspace').toString(),
      workspaceTargetLabel:
          (json['workspace_target_label'] ??
                  _defaultWorkspaceTargetLabel(
                    (json['workspace_target'] ?? 'workspace').toString(),
                  ))
              .toString(),
      workspaceBrief: (json['workspace_brief'] ?? '--').toString(),
    );
  }
}

class AssetInventory {
  const AssetInventory({
    required this.datasetAssets,
    required this.modelAssets,
    required this.knowledgeAssets,
    required this.optimizationAssets,
  });

  final int datasetAssets;
  final int modelAssets;
  final int knowledgeAssets;
  final int optimizationAssets;

  factory AssetInventory.fromJson(Map<String, dynamic> json) {
    return AssetInventory(
      datasetAssets: _asInt(json['dataset_assets']) ?? 0,
      modelAssets: _asInt(json['model_assets']) ?? 0,
      knowledgeAssets: _asInt(json['knowledge_assets']) ?? 0,
      optimizationAssets: _asInt(json['optimization_assets']) ?? 0,
    );
  }
}

class AssetDataset {
  const AssetDataset({
    required this.id,
    required this.filename,
    this.qualityScore,
    this.rows,
    this.columns,
    this.storageUrl,
    this.createdAt,
  });

  final String id;
  final String filename;
  final double? qualityScore;
  final int? rows;
  final int? columns;
  final String? storageUrl;
  final DateTime? createdAt;

  factory AssetDataset.fromJson(Map<String, dynamic> json) {
    return AssetDataset(
      id: (json['id'] ?? '').toString(),
      filename: (json['filename'] ?? 'Unknown').toString(),
      qualityScore: _asDouble(json['quality_score']),
      rows: _asInt(json['rows']),
      columns: _asInt(json['columns']),
      storageUrl: json['storage_url']?.toString(),
      createdAt: _parseDateTime(json['created_at']),
    );
  }
}

class AssetModel {
  const AssetModel({
    required this.jobId,
    required this.version,
    this.modelType,
    this.modelPath,
    this.targetColumn,
    this.storagePath,
    this.attemptCount,
    this.maxAttempts,
    this.completedAt,
  });

  final String jobId;
  final String version;
  final String? modelType;
  final String? modelPath;
  final String? targetColumn;
  final String? storagePath;
  final int? attemptCount;
  final int? maxAttempts;
  final DateTime? completedAt;

  factory AssetModel.fromJson(Map<String, dynamic> json) {
    return AssetModel(
      jobId: (json['job_id'] ?? '').toString(),
      version: (json['version'] ?? '--').toString(),
      modelType: json['model_type']?.toString(),
      modelPath: json['model_path']?.toString(),
      targetColumn: json['target_column']?.toString(),
      storagePath: json['storage_path']?.toString(),
      attemptCount: _asInt(json['attempt_count']),
      maxAttempts: _asInt(json['max_attempts']),
      completedAt: _parseDateTime(json['completed_at']),
    );
  }
}

class KnowledgeAsset {
  const KnowledgeAsset({
    required this.jobId,
    required this.version,
    this.collection,
    this.storagePath,
    this.count,
    this.reset,
    this.completedAt,
  });

  final String jobId;
  final String version;
  final String? collection;
  final String? storagePath;
  final int? count;
  final bool? reset;
  final DateTime? completedAt;

  factory KnowledgeAsset.fromJson(Map<String, dynamic> json) {
    return KnowledgeAsset(
      jobId: (json['job_id'] ?? '').toString(),
      version: (json['version'] ?? '--').toString(),
      collection: json['collection']?.toString(),
      storagePath: json['storage_path']?.toString(),
      count: _asInt(json['count']),
      reset: _asBool(json['reset']),
      completedAt: _parseDateTime(json['completed_at']),
    );
  }
}

class OptimizationAsset {
  const OptimizationAsset({
    required this.jobId,
    required this.version,
    this.targetDate,
    this.initialSoc,
    this.batteryCapacity,
    this.batteryPower,
    this.savings,
    this.savingsPercent,
    this.completedAt,
  });

  final String jobId;
  final String version;
  final String? targetDate;
  final double? initialSoc;
  final double? batteryCapacity;
  final double? batteryPower;
  final double? savings;
  final double? savingsPercent;
  final DateTime? completedAt;

  factory OptimizationAsset.fromJson(Map<String, dynamic> json) {
    return OptimizationAsset(
      jobId: (json['job_id'] ?? '').toString(),
      version: (json['version'] ?? '--').toString(),
      targetDate: json['target_date']?.toString(),
      initialSoc: _asDouble(json['initial_soc']),
      batteryCapacity: _asDouble(json['battery_capacity']),
      batteryPower: _asDouble(json['battery_power']),
      savings: _asDouble(json['savings']),
      savingsPercent: _asDouble(json['savings_percent']),
      completedAt: _parseDateTime(json['completed_at']),
    );
  }
}

class DashboardKpis {
  const DashboardKpis({
    required this.datasetCount,
    required this.analysisCount,
    required this.modelCount,
    required this.jobs24h,
    required this.failedJobs,
  });

  final int datasetCount;
  final int analysisCount;
  final int modelCount;
  final int jobs24h;
  final int failedJobs;

  factory DashboardKpis.fromJson(Map<String, dynamic> json) {
    return DashboardKpis(
      datasetCount: _asInt(json['dataset_count']) ?? 0,
      analysisCount: _asInt(json['analysis_count']) ?? 0,
      modelCount: _asInt(json['model_count']) ?? 0,
      jobs24h: _asInt(json['jobs_24h']) ?? 0,
      failedJobs: _asInt(json['failed_jobs']) ?? 0,
    );
  }
}

class SystemStatusItem {
  const SystemStatusItem({
    required this.key,
    required this.label,
    required this.status,
    required this.message,
  });

  final String key;
  final String label;
  final String status;
  final String message;

  factory SystemStatusItem.fromJson(Map<String, dynamic> json) {
    return SystemStatusItem(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      status: (json['status'] ?? 'unknown').toString(),
      message: (json['message'] ?? '').toString(),
    );
  }
}

class DatasetAsset {
  const DatasetAsset({
    required this.id,
    required this.filename,
    this.qualityScore,
    this.rows,
    this.columns,
    this.storageUrl,
    this.createdAt,
  });

  final String id;
  final String filename;
  final double? qualityScore;
  final int? rows;
  final int? columns;
  final String? storageUrl;
  final DateTime? createdAt;

  factory DatasetAsset.fromJson(Map<String, dynamic> json) {
    return DatasetAsset(
      id: (json['id'] ?? '').toString(),
      filename: (json['filename'] ?? 'Unknown').toString(),
      qualityScore: _asDouble(json['quality_score']),
      rows: _asInt(json['rows']),
      columns: _asInt(json['columns']),
      storageUrl: json['storage_url']?.toString(),
      createdAt: _parseDateTime(json['created_at']),
    );
  }
}

class DashboardAlert {
  const DashboardAlert({
    required this.severity,
    required this.title,
    required this.message,
    this.assetKey,
  });

  final String severity;
  final String title;
  final String message;
  final String? assetKey;

  factory DashboardAlert.fromJson(Map<String, dynamic> json) {
    return DashboardAlert(
      severity: (json['severity'] ?? 'info').toString(),
      title: (json['title'] ?? '系统提醒').toString(),
      message: (json['message'] ?? '').toString(),
      assetKey: json['asset_key']?.toString(),
    );
  }
}

List<T> _mapList<T>(Object? source, T Function(Map<String, dynamic>) parser) {
  if (source is! List) {
    return <T>[];
  }

  return source
      .whereType<Object?>()
      .map((item) {
        if (item is Map<String, dynamic>) {
          return parser(item);
        }
        if (item is Map) {
          return parser(Map<String, dynamic>.from(item));
        }
        return null;
      })
      .whereType<T>()
      .toList(growable: false);
}

List<String> _mapPrimitiveList(Object? source) {
  if (source is! List) {
    return const <String>[];
  }

  return source
      .map((item) => item?.toString().trim() ?? '')
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

int? _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}

double? _asDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

DateTime? _parseDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  if (value is String && value.isNotEmpty) {
    return DateTime.tryParse(value);
  }
  return null;
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    final normalized = value.toLowerCase();
    if (normalized == 'true' || normalized == '1') {
      return true;
    }
    if (normalized == 'false' || normalized == '0') {
      return false;
    }
  }
  return null;
}
