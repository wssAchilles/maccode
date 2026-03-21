import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/ai_lab_launch_intent.dart';
import 'package:front/models/job_record.dart';
import 'package:front/models/optimization_launch_intent.dart';
import 'package:front/widgets/history/history_asset_ledger.dart';

void main() {
  testWidgets('model ledger sends apply-model action into AI Lab', (
    tester,
  ) async {
    AiLabLaunchIntent? capturedIntent;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HistoryAssetLedger(
              jobs: [
                JobRecord(
                  jobId: 'train-job-12345678',
                  type: 'ml_train',
                  status: 'succeeded',
                  progress: 100,
                  requestedBy: 'tester',
                  attemptCount: 1,
                  maxAttempts: 3,
                  completedAt: DateTime.parse('2026-03-19T10:00:00Z'),
                  input: const {
                    'storage_path': 'uploads/demo.csv',
                    'target_column': 'load_mw',
                  },
                  result: const {
                    'model_path': 'models/demo.pt',
                    'model_type': 'lstm',
                    'target_column': 'load_mw',
                  },
                ),
              ],
              records: const [],
              onOpenAiLab: (intent) => capturedIntent = intent,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('回填训练入口'));
    await tester.tap(find.text('回填训练入口'));
    await tester.pumpAndSettle();

    expect(capturedIntent, isNotNull);
    expect(capturedIntent!.target, AiLabLaunchTarget.deepLearning);
    expect(capturedIntent!.storagePath, 'uploads/demo.csv');
    expect(capturedIntent!.targetColumn, 'load_mw');
    expect(capturedIntent!.sourceLabel, contains('模型资产台账'));
    expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
    expect(capturedIntent!.context?.cardTarget, 'runtime_product');
  });

  testWidgets('knowledge ledger sends apply-knowledge action into AI Lab', (
    tester,
  ) async {
    AiLabLaunchIntent? capturedIntent;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HistoryAssetLedger(
              jobs: [
                JobRecord(
                  jobId: 'rag-job-12345678',
                  type: 'rag_ingest',
                  status: 'succeeded',
                  progress: 100,
                  requestedBy: 'tester',
                  attemptCount: 1,
                  maxAttempts: 3,
                  completedAt: DateTime.parse('2026-03-19T10:00:00Z'),
                  input: const {
                    'storage_path': 'docs/knowledge',
                    'collection_name': 'ops-knowledge',
                    'reset': true,
                  },
                  result: const {
                    'storage_path': 'docs/knowledge',
                    'collection': 'ops-knowledge',
                    'count': 42,
                  },
                ),
              ],
              records: const [],
              onOpenAiLab: (intent) => capturedIntent = intent,
            ),
          ),
        ),
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
    expect(capturedIntent!.sourceLabel, contains('知识库资产台账'));
    expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
    expect(capturedIntent!.context?.cardTarget, 'runtime_product');
  });

  testWidgets('optimization ledger replays optimization into workbench', (
    tester,
  ) async {
    OptimizationLaunchIntent? capturedIntent;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HistoryAssetLedger(
              jobs: [
                JobRecord(
                  jobId: 'opt-job-12345678',
                  type: 'optimization',
                  status: 'succeeded',
                  progress: 100,
                  requestedBy: 'tester',
                  attemptCount: 1,
                  maxAttempts: 3,
                  completedAt: DateTime.parse('2026-03-19T10:00:00Z'),
                  input: const {
                    'initial_soc': 0.5,
                    'target_date': '2026-03-19T00:00:00Z',
                    'battery_capacity': 120.0,
                    'battery_power': 60.0,
                    'temperature_adjust': 1.0,
                  },
                  result: const {
                    'optimization': {
                      'summary': {'savings': 88.6},
                    },
                  },
                ),
              ],
              records: const [],
              onOpenOptimization: (intent) => capturedIntent = intent,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('回放优化'));
    await tester.tap(find.text('回放优化'));
    await tester.pumpAndSettle();

    expect(capturedIntent, isNotNull);
    expect(capturedIntent!.sourceLabel, contains('优化资产台账'));
    expect(capturedIntent!.context?.workspaceTarget, 'optimization_registry');
    expect(capturedIntent!.context?.cardTarget, 'latest_snapshot');
    expect(capturedIntent!.hasResultPayload, isTrue);
    expect(capturedIntent!.resultPayload?['optimization'], isNotNull);
  });
}
