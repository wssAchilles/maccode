import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/widgets/operations/ai_lab_operations_board.dart';

DashboardSummary _summary() {
  return DashboardSummary.fromJson({
    'system_status': [
      {
        'key': 'model',
        'label': 'Model',
        'status': 'healthy',
        'message': 'Forecast model metadata available',
      },
      {
        'key': 'rag',
        'label': 'RAG',
        'status': 'healthy',
        'message': 'Knowledge service ready',
      },
    ],
    'kpis': {
      'dataset_count': 0,
      'analysis_count': 0,
      'model_count': 3,
      'jobs_24h': 0,
      'failed_jobs': 0,
    },
    'duty_summary': {'overview_actions': [], 'audit_actions': []},
    'recent_jobs': [],
    'recent_assets': [],
    'recent_history': [],
    'alerts': [],
    'asset_summary': {
      'inventory': {
        'dataset_assets': 0,
        'model_assets': 0,
        'knowledge_assets': 0,
        'optimization_assets': 0,
      },
      'datasets': [],
      'models': [],
      'knowledge_bases': [],
      'optimizations': [],
      'failure_chains': [],
      'governance': [],
      'chain_summaries': [],
    },
  });
}

void main() {
  testWidgets('AiLabOperationsBoard localizes generic queue status summaries', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AiLabOperationsBoard(
              summary: _summary(),
              trainingJobs: const [
                JobRecord(
                  jobId: 'train-1',
                  type: 'ml_train',
                  status: 'succeeded',
                  progress: 100,
                  requestedBy: 'tester',
                  attemptCount: 1,
                  maxAttempts: 3,
                  statusMessage: 'Job completed',
                ),
              ],
              ragJobs: const [
                JobRecord(
                  jobId: 'rag-1',
                  type: 'rag_ingest',
                  status: 'queued',
                  progress: 0,
                  requestedBy: 'tester',
                  attemptCount: 0,
                  maxAttempts: 3,
                  statusMessage: 'queued',
                ),
              ],
              currentTab: 'deepLearning',
              trainingStoragePath: 'uploads/demo.csv',
              ragStoragePath: 'uploads/demo.csv',
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Job completed'), findsNothing);
    expect(find.text('queued'), findsNothing);
    expect(find.text('最近训练已完成'), findsWidgets);
    expect(find.text('知识库任务已排队'), findsWidgets);
  });
}
