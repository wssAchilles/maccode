import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/config/app_theme.dart';
import 'package:front/models/job_record.dart';
import 'package:front/widgets/operations/approval_queue_board.dart';

void main() {
  testWidgets('ApprovalQueueBoard renders queued approvals and actions', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: ApprovalQueueBoard(
            jobs: const [
              JobRecord(
                jobId: 'approval-1',
                operationId: 'approval-1',
                type: 'ml_train',
                status: 'awaiting_approval',
                progress: 0,
                requestedBy: 'tester',
                attemptCount: 0,
                maxAttempts: 3,
                approvalPolicy: {
                  'required': true,
                  'mode': 'manual',
                  'reason': '高成本重训需要审批',
                },
                currentStep: JobStep(
                  phase: 'train',
                  toolName: 'train_forecast_model',
                  status: 'running',
                  progress: 48,
                  message: '正在训练模型',
                ),
              ),
            ],
            isLoading: false,
            onRefresh: _noop,
            onApprove: _onApprove,
            onReject: _onApprove,
            isUpdating: (_) => false,
          ),
        ),
      ),
    );

    expect(find.text('审批中心'), findsOneWidget);
    expect(find.text('approval-1'), findsOneWidget);
    expect(find.text('待审批'), findsOneWidget);
    expect(find.textContaining('train · train_forecast_model'), findsOneWidget);
    expect(find.textContaining('高成本重训需要审批'), findsOneWidget);
    expect(find.text('批准执行'), findsOneWidget);
    expect(find.text('驳回任务'), findsOneWidget);
  });

  testWidgets('ApprovalQueueBoard renders empty hint', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: ApprovalQueueBoard(
            jobs: const [],
            isLoading: false,
            onRefresh: _noop,
            onApprove: _onApprove,
            onReject: _onApprove,
            isUpdating: (_) => false,
            errorMessage: '加载审批队列失败',
          ),
        ),
      ),
    );

    expect(find.text('加载审批队列失败'), findsOneWidget);
    expect(find.text('刷新队列'), findsOneWidget);
  });
}

void _noop() {}
void _onApprove(JobRecord _) {}
