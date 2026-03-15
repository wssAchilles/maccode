import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/workbench_launch_context.dart';
import 'package:front/utils/asset_chain_context.dart';

void main() {
  group('buildLaunchArrivalMessage', () {
    test('preserves explicit duty labels for generic AI Lab open', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: 'Duty Actions · 打开 AI Lab',
        workspaceTarget: 'ai_runtime',
        workspaceTargetLabel: 'AI 运行控制区',
        cardTarget: 'runtime_product',
        cardTargetLabel: '运行产物',
        incidentTarget: 'runtime',
        incidentTargetLabel: '运行态',
        workspaceBrief: 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
        watchSummary: '运行态 · AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: 'AI Lab',
        destination: 'AI Lab',
      );

      expect(message, 'Duty Actions · 打开 AI Lab · AI 运行控制区 · 运行产物 · AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。');
    });

    test('does not duplicate destination when subject already contains it', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: 'Duty Actions · 打开 AI Lab',
        workspaceTarget: 'ai_runtime',
        workspaceTargetLabel: 'AI 运行控制区',
        cardTarget: 'runtime_product',
        cardTargetLabel: '运行产物',
        incidentTarget: 'runtime',
        incidentTargetLabel: '运行态',
        workspaceBrief: 'AI Lab 工作台已打开。',
        watchSummary: '运行态 · AI Lab 工作台已打开。',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: 'AI Lab',
        destination: 'AI Lab',
      );

      expect(message.contains('打开 AI Lab已打开AI Lab'), isFalse);
      expect(message.startsWith('Duty Actions · 打开 AI Lab'), isTrue);
    });

    test('compacts duplicated context parts already embedded in source label', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: '数据资产台账 · 资产治理板 · 当前资产 · 数据资产已载入当前资产',
        workspaceTarget: 'data_governance',
        workspaceTargetLabel: '资产治理板',
        cardTarget: 'current_asset',
        cardTargetLabel: '当前资产',
        incidentTarget: 'asset',
        incidentTargetLabel: '资产',
        workspaceBrief: '数据资产已载入当前资产',
        watchSummary: '资产 · 数据资产已载入当前资产',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: '数据分析工作台',
        destination: '数据分析工作台',
      );

      expect(message, '数据资产台账已打开数据分析工作台 · 资产治理板 · 当前资产 · 数据资产已载入当前资产');
    });

    test('keeps history send-to-training arrival concise', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: '数据资产台账',
        workspaceTarget: 'ai_runtime',
        workspaceTargetLabel: 'AI 运行控制区',
        cardTarget: 'runtime_product',
        cardTargetLabel: '运行产物',
        incidentTarget: 'runtime',
        incidentTargetLabel: '运行态',
        workspaceBrief: '数据资产已送入训练入口',
        watchSummary: '运行态 · 数据资产已送入训练入口',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: 'AI Lab',
        destination: 'AI Lab',
        verb: '已送入',
      );

      expect(message, '数据资产台账已送入 AI Lab · AI 运行控制区 · 运行产物 · 数据资产已送入训练入口');
    });

    test('keeps history replay optimization arrival concise', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: '优化资产台账',
        workspaceTarget: 'optimization_registry',
        workspaceTargetLabel: '优化注册表',
        cardTarget: 'latest_snapshot',
        cardTargetLabel: '最新快照',
        incidentTarget: 'asset',
        incidentTargetLabel: '资产',
        workspaceBrief: '优化快照已载入结果工作台',
        watchSummary: '资产 · 优化快照已载入结果工作台',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: '优化工作台',
        destination: '优化工作台',
        verb: '已载入',
      );

      expect(message, '优化资产台账已载入优化工作台 · 优化注册表 · 最新快照 · 优化快照已载入结果工作台');
    });

    test('keeps history failure-chain AI Lab arrival concise', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: '模型训练失败链路 · AI 运行控制区 · 当前卡片 · completed · 100% · 运行控制区',
        workspaceTarget: 'ai_runtime',
        workspaceTargetLabel: 'AI 运行控制区',
        cardTarget: 'current_asset',
        cardTargetLabel: '当前卡片',
        incidentTarget: 'asset',
        incidentTargetLabel: '资产',
        workspaceBrief: 'completed · 100% · 运行控制区',
        watchSummary: '资产 · completed · 100% · 运行控制区',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: 'AI Lab',
        destination: 'AI Lab',
        verb: '已送入',
        includeWorkspaceBrief: false,
      );

      expect(message, '模型训练失败链路已送入 AI Lab · AI 运行控制区 · 当前卡片');
    });
  });

    test('inserts a space before English workbench names in mixed-language phrases', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: '数据资产台账',
        workspaceTarget: 'ai_runtime',
        workspaceTargetLabel: 'AI 运行控制区',
        cardTarget: 'runtime_product',
        cardTargetLabel: '运行产物',
        incidentTarget: 'runtime',
        incidentTargetLabel: '运行态',
        workspaceBrief: '数据资产已送入训练入口',
        watchSummary: '运行态 · 数据资产已送入训练入口',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: 'AI Lab',
        destination: 'AI Lab',
        verb: '已送入',
      );

      expect(message, '数据资产台账已送入 AI Lab · AI 运行控制区 · 运行产物 · 数据资产已送入训练入口');
    });

    test('keeps Chinese workbench names compact without extra spaces', () {
      const context = WorkbenchLaunchContext(
        sourceLabel: 'Duty Actions · 上传并分析数据',
        workspaceTarget: 'data_analysis_operations',
        workspaceTargetLabel: '分析执行区',
        cardTarget: 'strategy',
        cardTargetLabel: '执行策略',
        incidentTarget: 'asset',
        incidentTargetLabel: '资产',
        workspaceBrief: '数据分析工作台 · 上传 CSV、审查质量并启动分析任务。',
        watchSummary: '资产 · 数据分析工作台 · 上传 CSV、审查质量并启动分析任务。',
      );

      final message = buildLaunchArrivalMessage(
        context,
        fallbackSubject: '数据分析工作台',
        destination: '数据分析工作台',
      );

      expect(message, 'Duty Actions · 上传并分析数据已打开数据分析工作台 · 分析执行区 · 执行策略 · 数据分析工作台 · 上传 CSV、审查质量并启动分析任务。');
    });


  group('buildLaunchContextFromDutyAction', () {
    test('applies dataset fallback workspace and card targets', () {
      const action = DutyAction(
        command: 'open_workspace',
        label: '上传并分析数据',
        tone: 'primary',
        chainKey: 'dataset',
        chainLabel: '数据资产',
        workspaceTarget: 'workspace',
        workspaceTargetLabel: '工作台',
        cardTarget: 'summary',
        cardTargetLabel: '当前卡片',
        incidentTarget: 'focus',
        incidentTargetLabel: '当前焦点',
        workspaceBrief: '--',
      );

      final context = buildLaunchContextFromDutyAction(
        action,
        prefix: 'Duty Actions',
      );

      expect(context.workspaceTarget, 'data_analysis_operations');
      expect(context.workspaceTargetLabel, '分析执行区');
      expect(context.cardTarget, 'strategy');
      expect(context.cardTargetLabel, '执行策略');
      expect(context.incidentTarget, 'asset');
      expect(context.sourceLabel, 'Duty Actions · 上传并分析数据');
    });

    test('applies knowledge fallback workspace brief', () {
      const action = DutyAction(
        command: 'open_workspace',
        label: '构建知识库',
        tone: 'primary',
        chainKey: 'knowledge',
        chainLabel: '知识资产',
        workspaceTarget: 'workspace',
        workspaceTargetLabel: '工作台',
        cardTarget: 'summary',
        cardTargetLabel: '当前卡片',
        incidentTarget: 'focus',
        incidentTargetLabel: '当前焦点',
        workspaceBrief: '--',
      );

      final context = buildLaunchContextFromDutyAction(
        action,
        prefix: 'Duty Actions',
      );

      expect(context.workspaceTarget, 'ai_runtime');
      expect(context.cardTarget, 'runtime_product');
      expect(context.workspaceBrief, contains('AI Lab 知识车道'));
      expect(context.watchSummary, contains('AI Lab 知识车道'));
    });
  });

  group('buildChainActionFeedbackMessage', () {
    test('omits incident label for compact action feedback', () {
      expect(
        buildChainActionFeedbackMessage(
          _chain(
            workspaceTargetLabel: 'AI 运行控制区',
            cardTargetLabel: '当前卡片',
            incidentTargetLabel: '值班时限',
          ),
          prefix: '知识快照护照已复制',
        ),
        '知识快照护照已复制 · AI 运行控制区 · 当前卡片',
      );
    });

    test('appends detail to compact action feedback', () {
      expect(
        buildChainActionFeedbackMessage(
          _chain(
            workspaceTargetLabel: '优化注册表',
            cardTargetLabel: '当前卡片',
          ),
          prefix: '后台优化任务已提交',
          detail: 'job-1234',
        ),
        '后台优化任务已提交 · 优化注册表 · 当前卡片 · job-1234',
      );
    });
  });

  group('buildIncidentWatchValue', () {
    test('deduplicates incident label and watch summary fragments', () {
      final value = buildIncidentWatchValue(
        '值班时限',
        '值班时限 · 还剩 12 分钟',
      );

      expect(value, '值班时限 · 还剩 12 分钟');
    });
  });
}

AssetChainSummary _chain({
  String key = 'dataset',
  String label = '数据资产',
  String workspaceTarget = 'data_governance',
  String workspaceTargetLabel = '资产治理板',
  String cardTarget = 'current_asset',
  String cardTargetLabel = '当前资产',
  String incidentTarget = 'asset',
  String incidentTargetLabel = '资产',
  String workspaceBrief = '当前资产已载入工作台',
  String incidentBrief = '资产 · 当前资产已载入工作台',
}) {
  return AssetChainSummary(
    key: key,
    label: label,
    status: 'healthy',
    statusLabel: '正常',
    priorityScore: 10,
    ownerLabel: '值班人',
    slaMinutes: 30,
    escalationLabel: '仍在 SLA 内',
    elapsedMinutes: 5,
    overdueMinutes: 0,
    isOverdue: false,
    escalationTier: 0,
    escalationStateLabel: '正常',
    latestVersion: 'v1',
    latestLabel: '最新版本',
    lineageSummary: 'lineage',
    failureSummary: 'none',
    focusLabel: '资产',
    focusDetail: '',
    focusTarget: cardTarget,
    focusTargetLabel: cardTargetLabel,
    sectionTarget: workspaceTarget,
    sectionTargetLabel: workspaceTargetLabel,
    workspaceTarget: workspaceTarget,
    workspaceTargetLabel: workspaceTargetLabel,
    workspaceBrief: workspaceBrief,
    cardTarget: cardTarget,
    cardTargetLabel: cardTargetLabel,
    incidentTarget: incidentTarget,
    incidentTargetLabel: incidentTargetLabel,
    incidentBrief: incidentBrief,
    narrativeTarget: 'target',
    narrativeTargetLabel: '当前卡片',
    dispositionTarget: 'focus',
    dispositionTargetLabel: '当前卡片',
    runbookTitle: 'runbook',
    runbookSteps: const ['step 1'],
    activityTitle: 'activity',
    activityStatus: 'active',
    activitySource: 'unit-test',
    failurePhase: 'none',
    failureSource: 'none',
    jobStatus: 'succeeded',
    jobProgress: 100,
    jobPhase: 'completed',
    actionLabel: 'open_workspace',
    timeline: const [],
  );
}
