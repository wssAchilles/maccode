import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/models/job_stream_frame.dart';
import 'package:front/repositories/audit_repository.dart';
import 'package:front/repositories/dashboard_repository.dart';
import 'package:front/repositories/job_repository.dart';
import 'package:front/screens/data_analysis_screen.dart';
import 'package:front/screens/history_audit_screen.dart';
import 'package:front/screens/ai_lab_screen.dart';
import 'package:front/screens/modeling_screen.dart';
import 'package:front/screens/operations_hub_screen.dart';
import 'package:front/services/api_service_exception.dart';
import 'package:front/services/auth_gateway.dart';
import 'package:front/services/data_analysis_gateway.dart';
import 'package:front/services/history_gateway.dart';
import 'package:front/services/optimization_gateway.dart';
import 'package:front/viewmodels/audit_view_model.dart';
import 'package:front/viewmodels/dashboard_view_model.dart';
import 'package:front/viewmodels/data_analysis_view_model.dart';
import 'package:front/viewmodels/history_view_model.dart';
import 'package:front/viewmodels/job_view_model.dart';
import 'package:front/viewmodels/modeling_view_model.dart';
import 'package:front/models/optimization_result.dart';
import 'package:front/widgets/analysis/data_analysis_sliver_app_bar.dart';
import 'package:front/widgets/operations/embedded_page_header.dart';
import 'package:front/widgets/operations/workbench_page_frame.dart';

class _FakeUser extends Fake implements User {
  _FakeUser({required this.email});

  @override
  final String? email;

  @override
  String? get displayName => null;

  @override
  bool get emailVerified => true;

  @override
  String get uid => 'embedded-shell-user';

  @override
  String? get photoURL => null;
}

class _FakeUserCredential extends Fake implements UserCredential {
  _FakeUserCredential(this._user);

  final User _user;

  @override
  User? get user => _user;
}

class _FakeAuthGateway implements AuthGateway {
  _FakeAuthGateway({this.currentUserValue});

  final User? currentUserValue;

  @override
  User? get currentUser => currentUserValue;

  @override
  Stream<User?> get authStateChanges => const Stream<User?>.empty();

  @override
  Future<UserCredential> registerWithEmail({required String email, required String password}) async {
    return _FakeUserCredential(_FakeUser(email: email));
  }

  @override
  Future<UserCredential> signInWithEmail({required String email, required String password}) async {
    return _FakeUserCredential(_FakeUser(email: email));
  }

  @override
  Future<UserCredential> signInWithGoogle() async {
    return _FakeUserCredential(_FakeUser(email: 'user@example.com'));
  }

  @override
  Future<void> signOut() async {}
}

class _FakeDataAnalysisGateway implements DataAnalysisGateway {
  @override
  Future<AnalysisResult> analyzeCsv({required String storagePath, String? filename, bool saveToStorage = true}) async {
    throw const ApiServiceException('not used in embedded shell test');
  }

  @override
  Future<Map<String, dynamic>> createAnalysisJob({required String storagePath, String? filename, bool saveToStorage = true}) async {
    return {
      'job_id': 'analysis-job-1',
      'type': 'analysis',
      'status': 'queued',
      'progress': 0,
      'requested_by': 'test-user',
      'attempt_count': 0,
      'max_attempts': 1,
      'input': {'storage_path': storagePath},
      'result': const <String, dynamic>{},
      'retryable': false,
      'events': const <Map<String, dynamic>>[],
    };
  }

  @override
  Future<Map<String, dynamic>> detectDataDrift({required String referencePath, required String currentPath, required List<String> features}) async {
    return {
      'drift_results': {
        'overall_status': 'stable',
        'recommendation': 'ok',
        'summary': {'stable': 1, 'warning': 0, 'drift': 0},
        'features': const <String, dynamic>{},
      },
      'report': '# ok',
    };
  }

  @override
  Future<Map<String, dynamic>> getUploadUrl({required String fileName, required String contentType}) async {
    return {
      'uploadUrl': 'https://upload.example.com/signed',
      'storagePath': 'uploads/$fileName',
    };
  }

  @override
  Future<void> uploadFileToGcs({required String uploadUrl, required List<int> fileData, required String contentType}) async {}
}



class _FakeOptimizationGateway implements OptimizationGateway {
  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) async {
    return OptimizationResponse.fromJson({
      'success': true,
      'model_info': {
        'model_type': 'random_forest',
        'status': 'active',
        'training_samples': 8760,
      },
      'optimization': {
        'status': 'Optimal',
        'chart_data': <dynamic>[],
        'summary': {
          'total_cost_without_battery': 1000,
          'total_cost_with_battery': 800,
          'savings': 200,
          'savings_percent': 20,
          'total_load': 5000,
          'total_charged': 800,
          'total_discharged': 700,
          'peak_load': 350,
          'min_load': 120,
          'avg_load': 210,
        },
        'strategy': {
          'charging_hours': [1, 2, 3],
          'discharging_hours': [18, 19],
          'charging_count': 3,
          'discharging_count': 2,
        },
      },
    });
  }
}
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
  Future<List<JobRecord>> listJobs({String? type, String? status, int limit = 20}) async => jobs;

  @override
  Future<JobRecord> getJob(String jobId) async => jobs.first;

  @override
  Future<JobRecord> retryJob(String jobId) => throw UnimplementedError();

  @override
  Future<JobRecord> cancelJob(String jobId, {String? operationId}) =>
      throw UnimplementedError();

  @override
  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) => throw UnimplementedError();

  @override
  Stream<JobStreamFrame> streamJob(String jobId, {String? operationId}) =>
      const Stream<JobStreamFrame>.empty();

  @override
  Future<JobRecord> createOptimizationJob({required double initialSoc, DateTime? targetDate, double? batteryCapacity, double? batteryPower, double? batteryEfficiency, double? temperatureAdjust}) => throw UnimplementedError();

  @override
  Future<JobRecord> createMlTrainJob({required String storagePath, required String modelType, required int epochs, required int batchSize, required int windowSize, required String targetColumn}) => throw UnimplementedError();

  @override
  Future<JobRecord> createRagIngestJob({required String storagePath, String? collectionName, bool reset = false}) => throw UnimplementedError();
}

class _FakeAuditRepository implements AuditRepository {
  const _FakeAuditRepository();

  @override
  Future<List<AuditActivity>> getActivity({String? type, String? status, int limit = 50}) async => const [];
}

class _FakeHistoryGateway implements HistoryGateway {
  const _FakeHistoryGateway();

  @override
  Future<void> deleteHistoryRecord(String recordId) async {}

  @override
  Future<List<Map<String, dynamic>>> getAuditActivity({String? type, String? status, int limit = 50}) async => const [];

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 30}) async => const [];
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
      'focus_chain_key': 'dataset',
      'focus_chain_label': '数据资产',
      'focus_workspace_target': 'data_governance',
      'focus_workspace_target_label': '资产治理板',
      'focus_card_target': 'strategy',
      'focus_card_target_label': '执行策略',
      'focus_incident_target': 'asset',
      'focus_incident_target_label': '资产状态',
      'focus_watch': '优先查看治理与交接。',
      'focus_owner_label': 'DataOps',
      'focus_escalation_state_label': '观察中',
      'overview_actions': [],
      'audit_actions': [],
    },
    'recent_jobs': const [],
    'recent_assets': const [],
    'recent_history': const [],
    'alerts': const [],
    'asset_summary': {
      'inventory': const {
        'dataset_assets': 1,
        'model_assets': 0,
        'knowledge_assets': 0,
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
          'key': 'dataset',
          'label': '数据资产',
          'status': 'healthy',
          'status_label': '链路健康',
          'priority_score': 60,
          'owner_label': 'DataOps',
          'sla_minutes': 30,
          'escalation_label': 'P2',
          'elapsed_minutes': 5,
          'overdue_minutes': 0,
          'is_overdue': false,
          'escalation_tier': 1,
          'escalation_state_label': '观察中',
          'latest_version': 'v1',
          'latest_label': 'latest',
          'lineage_summary': 'dataset lineage',
          'failure_summary': '--',
          'focus_label': '当前资产',
          'focus_detail': '上传并分析数据',
          'focus_target': 'dataset_current_asset',
          'focus_target_label': '当前资产',
          'section_target': 'data_analysis_operations',
          'section_target_label': '运营态工作台',
          'workspace_target': 'data_governance',
          'workspace_target_label': '资产治理板',
          'workspace_brief': '数据分析工作台 · 上传数据并查看治理和结果。',
          'card_target': 'strategy',
          'card_target_label': '执行策略',
          'incident_target': 'asset',
          'incident_target_label': '资产状态',
          'incident_brief': '数据资产状态正常',
          'narrative_target': 'target',
          'narrative_target_label': '目标落点',
          'disposition_target': 'focus',
          'disposition_target_label': '当前焦点',
          'runbook_title': '数据资产 Runbook',
          'runbook_steps': ['检查数据'],
          'activity_title': '最近分析',
          'activity_status': 'idle',
          'activity_source': 'dashboard',
          'failure_phase': '--',
          'failure_source': '--',
          'job_status': '--',
          'job_progress': 0,
          'job_phase': '--',
          'action_label': '打开数据分析',
          'timeline': [],
        },
      ],
    },
  });
}

Widget _embeddedHarness(Widget child) {
  return MaterialApp(
    home: Scaffold(
      body: child,
    ),
  );
}

void main() {
  testWidgets('DataAnalysisScreen embedded mode does not render standalone app bars', (tester) async {
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(currentUserValue: _FakeUser(email: 'user@example.com')),
      dataGateway: _FakeDataAnalysisGateway(),
    );
    addTearDown(viewModel.dispose);
    viewModel.setPickedFileForTesting(
      PlatformFile(name: 'sample.csv', size: 2, bytes: Uint8List.fromList([1, 2])),
    );

    await tester.pumpWidget(
      _embeddedHarness(
        DataAnalysisScreen(
          viewModel: viewModel,
          dashboardViewModel: DashboardViewModel(repository: _FakeDashboardRepository(_buildSummary())),
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(DataAnalysisSliverAppBar), findsNothing);
    expect(find.byType(EmbeddedPageHeader), findsOneWidget);
    expect(find.text('页级动作'), findsOneWidget);
  });

  testWidgets('HistoryAuditScreen embedded mode keeps content header without standalone app bar', (tester) async {
    final jobsViewModel = JobViewModel(repository: const _FakeJobRepository([]), delay: (_) async {});
    final auditViewModel = AuditViewModel(repository: const _FakeAuditRepository());
    final historyViewModel = HistoryViewModel(gateway: const _FakeHistoryGateway());

    await tester.pumpWidget(
      _embeddedHarness(
        HistoryAuditScreen(
          dashboardViewModel: DashboardViewModel(repository: _FakeDashboardRepository(_buildSummary())),
          jobsViewModel: jobsViewModel,
          auditViewModel: auditViewModel,
          historyViewModel: historyViewModel,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(EmbeddedPageHeader), findsOneWidget);
    expect(find.text('历史与审计'), findsOneWidget);
    expect(find.text('页级动作'), findsOneWidget);

    addTearDown(jobsViewModel.dispose);
    addTearDown(auditViewModel.dispose);
    addTearDown(historyViewModel.dispose);
  });


  testWidgets('OperationsHubScreen embedded mode keeps content header without standalone app bar', (tester) async {
    final viewModel = DashboardViewModel(repository: _FakeDashboardRepository(_buildSummary()));

    await tester.pumpWidget(
      _embeddedHarness(
        OperationsHubScreen(
          viewModel: viewModel,
          onNavigateToTab: (_) {},
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(EmbeddedPageHeader), findsOneWidget);
    expect(find.text('Operations Hub'), findsOneWidget);
  });

  testWidgets('ModelingScreen embedded mode keeps content header without standalone app bar', (tester) async {
    final viewModel = ModelingViewModel(gateway: _FakeOptimizationGateway());
    addTearDown(viewModel.dispose);

    await tester.pumpWidget(
      _embeddedHarness(
        ModelingScreen(
          viewModel: viewModel,
          dashboardViewModel: DashboardViewModel(repository: _FakeDashboardRepository(_buildSummary())),
          surfaceMode: WorkbenchSurfaceMode.embedded,
          nowBuilder: () => DateTime(2026, 3, 19),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(EmbeddedPageHeader), findsOneWidget);
    expect(find.text('Optimization Workbench'), findsOneWidget);
  });

  testWidgets('AiLabScreen embedded mode keeps content header without standalone app bar', (tester) async {
    final dashboardViewModel = DashboardViewModel(
      repository: _FakeDashboardRepository(_buildSummary()),
    );
    addTearDown(dashboardViewModel.dispose);

    await tester.pumpWidget(
      _embeddedHarness(
        AiLabScreen(
          dashboardViewModel: dashboardViewModel,
          surfaceMode: WorkbenchSurfaceMode.embedded,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(EmbeddedPageHeader), findsOneWidget);
    expect(find.text('AI Lab'), findsOneWidget);
    expect(find.text('页级动作'), findsOneWidget);
  });

}
