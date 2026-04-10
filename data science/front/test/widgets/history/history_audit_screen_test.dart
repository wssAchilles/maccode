import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/ai_lab_launch_intent.dart';
import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/models/job_stream_frame.dart';
import 'package:front/repositories/audit_repository.dart';
import 'package:front/repositories/dashboard_repository.dart';
import 'package:front/repositories/job_repository.dart';
import 'package:front/screens/history_audit_screen.dart';
import 'package:front/services/history_gateway.dart';
import 'package:front/viewmodels/audit_view_model.dart';
import 'package:front/viewmodels/dashboard_view_model.dart';
import 'package:front/viewmodels/history_view_model.dart';
import 'package:front/viewmodels/job_view_model.dart';
import 'package:front/widgets/operations/workbench_page_frame.dart';

class _FakeDashboardRepository implements DashboardRepository {
  const _FakeDashboardRepository(this.summary);

  final DashboardSummary summary;

  @override
  Future<DashboardSummary> getSummary() async => summary;
}

class _FakeJobRepository implements JobRepository {
  const _FakeJobRepository(this.jobs);

  final List<JobRecord> jobs;

  @override
  bool get supportsStreaming => false;

  @override
  Future<List<JobRecord>> listJobs({
    String? type,
    String? status,
    int limit = 20,
    String scope = 'private',
  }) async {
    return jobs;
  }

  @override
  Future<JobRecord> getJob(String jobId) async => jobs.first;

  @override
  Future<JobRecord> retryJob(String jobId) {
    throw UnimplementedError();
  }

  @override
  Future<JobRecord> cancelJob(String jobId, {String? operationId}) {
    throw UnimplementedError();
  }

  @override
  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) {
    throw UnimplementedError();
  }

  @override
  Stream<JobStreamFrame> streamJob(String jobId, {String? operationId}) =>
      const Stream<JobStreamFrame>.empty();

  @override
  Future<JobRecord> createOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<JobRecord> createMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<JobRecord> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) {
    throw UnimplementedError();
  }
}

class _FakeAuditRepository implements AuditRepository {
  const _FakeAuditRepository();

  final List<AuditActivity> activity = const [];

  @override
  Future<List<AuditActivity>> getActivity({
    String? type,
    String? status,
    int limit = 50,
  }) async => activity;
}

class _FakeHistoryGateway implements HistoryGateway {
  const _FakeHistoryGateway();

  final List<Map<String, dynamic>> records = const [];
  final List<Map<String, dynamic>> activity = const [];

  @override
  Future<void> deleteHistoryRecord(String recordId) async {}

  @override
  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 50,
  }) async => activity;

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 30}) async =>
      records;
}

DashboardSummary _buildSummary() {
  return DashboardSummary.fromJson({
    'system_status': const [
      {'key': 'api', 'label': 'API', 'status': 'healthy', 'message': 'ok'},
    ],
    'kpis': const {
      'dataset_count': 1,
      'analysis_count': 1,
      'model_count': 1,
      'jobs_24h': 1,
      'failed_jobs': 0,
    },
    'duty_summary': const {
      'focus_chain_key': 'knowledge',
      'focus_chain_label': '知识快照',
      'focus_workspace_target': 'ai_runtime',
      'focus_workspace_target_label': 'AI 运行控制区',
      'focus_card_target': 'runtime_product',
      'focus_card_target_label': '运行产物',
      'focus_incident_target': 'runtime',
      'focus_incident_target_label': '运行态',
      'focus_watch': '优先核对集合配置和最新知识快照。',
      'focus_owner_label': 'AI 知识平台主管',
      'focus_escalation_state_label': 'SLA 已超时',
      'audit_actions': [
        {
          'command': 'open_workspace',
          'label': '打开 AI Lab',
          'tone': 'primary',
          'chain_key': 'knowledge',
          'chain_label': '知识快照',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '运行态',
          'workspace_brief': 'AI Lab 知识车道 · 提交构建任务并跟进知识快照、问答治理。',
        },
      ],
      'overview_actions': [],
    },
    'recent_jobs': const [],
    'recent_assets': const [],
    'recent_history': const [],
    'alerts': const [],
    'asset_summary': {
      'inventory': const {
        'dataset_assets': 0,
        'model_assets': 0,
        'knowledge_assets': 1,
        'optimization_assets': 0,
      },
      'datasets': const [],
      'models': const [],
      'knowledge_bases': const [],
      'optimizations': const [],
      'failure_chains': const [],
      'governance': const [],
      'chain_summaries': const [
        {
          'key': 'knowledge',
          'label': '知识快照',
          'status': 'incident',
          'status_label': '故障待处置',
          'priority_score': 300,
          'owner_label': 'AI 知识平台主管',
          'sla_minutes': 15,
          'escalation_label': '升级到 AI 知识平台主管',
          'elapsed_minutes': 30,
          'overdue_minutes': 15,
          'is_overdue': true,
          'escalation_tier': 2,
          'escalation_state_label': 'SLA 已超时',
          'latest_version': 'v0314-0702',
          'latest_label': '20251209_130622_AEP_hourly',
          'lineage_summary': 'uploads/demo.csv -> ops-knowledge',
          'failure_summary': '--',
          'focus_label': '知识快照',
          'focus_detail': '回填知识入口',
          'focus_target': 'knowledge_runtime',
          'focus_target_label': '知识运行态',
          'section_target': 'ai_lab_runtime',
          'section_target_label': '运行控制区',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'workspace_brief': 'AI Lab 知识车道 · 提交构建任务并跟进知识快照、问答治理。',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '运行态',
          'incident_brief': '优先核对集合配置和最新知识快照。',
          'narrative_target': 'job',
          'narrative_target_label': '活跃作业',
          'disposition_target': 'job',
          'disposition_target_label': '活跃作业',
          'runbook_title': '知识库构建 Runbook',
          'runbook_steps': ['回填知识入口'],
          'activity_title': '最近知识库任务',
          'activity_status': 'succeeded',
          'activity_source': 'dashboard',
          'failure_phase': '--',
          'failure_source': '--',
          'job_status': 'succeeded',
          'job_progress': 100,
          'job_phase': 'completed',
          'action_label': '打开 AI Lab',
          'timeline': [],
        },
      ],
    },
  });
}

Widget _buildHarness({
  required DashboardSummary summary,
  required JobViewModel jobsViewModel,
  required AuditViewModel auditViewModel,
  required HistoryViewModel historyViewModel,
  ValueChanged<AiLabLaunchIntent>? onOpenAiLab,
}) {
  return MaterialApp(
    home: Scaffold(
      body: HistoryAuditScreen(
        dashboardViewModel: DashboardViewModel(
          repository: _FakeDashboardRepository(summary),
        ),
        jobsViewModel: jobsViewModel,
        auditViewModel: auditViewModel,
        historyViewModel: historyViewModel,
        onOpenAiLab: onOpenAiLab,
        surfaceMode: WorkbenchSurfaceMode.embedded,
      ),
    ),
  );
}

void main() {
  testWidgets('HistoryAuditScreen dispatches duty action open AI Lab', (
    tester,
  ) async {
    AiLabLaunchIntent? capturedIntent;
    final jobsViewModel = JobViewModel(
      repository: const _FakeJobRepository([]),
      delay: (_) async {},
    );
    final auditViewModel = AuditViewModel(
      repository: const _FakeAuditRepository(),
    );
    final historyViewModel = HistoryViewModel(
      gateway: const _FakeHistoryGateway(),
    );

    await tester.pumpWidget(
      _buildHarness(
        summary: _buildSummary(),
        jobsViewModel: jobsViewModel,
        auditViewModel: auditViewModel,
        historyViewModel: historyViewModel,
        onOpenAiLab: (intent) => capturedIntent = intent,
      ),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('打开 AI Lab').first);
    await tester.tap(find.text('打开 AI Lab').first);
    await tester.pumpAndSettle();

    expect(capturedIntent, isNotNull);
    expect(capturedIntent!.target, AiLabLaunchTarget.rag);
    expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
    expect(capturedIntent!.context?.cardTarget, 'runtime_product');
    expect(capturedIntent!.sourceLabel, contains('值班动作'));
  });

  testWidgets(
    'HistoryAuditScreen dispatches knowledge ledger action into AI Lab',
    (tester) async {
      AiLabLaunchIntent? capturedIntent;
      final jobsViewModel = JobViewModel(
        repository: const _FakeJobRepository([
          JobRecord(
            jobId: 'rag-job-12345678',
            type: 'rag_ingest',
            status: 'succeeded',
            progress: 100,
            requestedBy: 'tester',
            attemptCount: 1,
            maxAttempts: 3,
            completedAt: null,
            input: {
              'storage_path': 'docs/knowledge',
              'collection_name': 'ops-knowledge',
              'reset': true,
            },
            result: {
              'storage_path': 'docs/knowledge',
              'collection': 'ops-knowledge',
              'count': 42,
            },
          ),
        ]),
        delay: (_) async {},
      );
      final auditViewModel = AuditViewModel(
        repository: const _FakeAuditRepository(),
      );
      final historyViewModel = HistoryViewModel(
        gateway: const _FakeHistoryGateway(),
      );

      await tester.pumpWidget(
        _buildHarness(
          summary: _buildSummary(),
          jobsViewModel: jobsViewModel,
          auditViewModel: auditViewModel,
          historyViewModel: historyViewModel,
          onOpenAiLab: (intent) => capturedIntent = intent,
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.text('回填知识入口'));
      await tester.tap(find.text('回填知识入口'));
      await tester.pumpAndSettle();

      expect(capturedIntent, isNotNull);
      expect(capturedIntent!.target, AiLabLaunchTarget.rag);
      expect(capturedIntent!.storagePath, 'docs/knowledge');
      expect(capturedIntent!.collectionName, 'ops-knowledge');
      expect(capturedIntent!.resetCollection, isTrue);
      expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
      expect(capturedIntent!.context?.cardTarget, 'runtime_product');
      expect(capturedIntent!.sourceLabel, contains('知识库资产台账'));
    },
  );
}
