import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/config/app_theme.dart';
import 'package:front/models/control_task_record.dart';
import 'package:front/widgets/operations/control_task_board.dart';

void main() {
  testWidgets('ControlTaskBoard renders planning task details', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: ControlTaskBoard(
            tasks: const [
              ControlTaskRecord(
                id: 'train_model_daily',
                kind: 'scheduler',
                operationType: 'train_model',
                title: '每日模型重训',
                schedule: 'every day 04:00 UTC',
                defaultInput: {'task_name': 'train_model'},
                dependencies: ['dataset_ready'],
                approvalPolicy: {'required': false, 'mode': 'auto'},
                enabled: true,
                owner: 'system',
              ),
            ],
            isLoading: false,
            onRetry: _noop,
            onRunTask: _onRun,
            isTaskRunning: (_) => false,
            onToggleTask: _onRun,
            isTaskUpdating: (_) => false,
            onToggleApproval: _onRun,
            onEditDefinition: _onRun,
          ),
        ),
      ),
    );

    expect(find.text('规划任务'), findsOneWidget);
    expect(find.text('每日模型重训'), findsOneWidget);
    expect(find.text('every day 04:00 UTC'), findsOneWidget);
    expect(find.text('train_model'), findsOneWidget);
    expect(find.text('system'), findsOneWidget);
    expect(find.text('立即运行'), findsOneWidget);
    expect(find.text('暂停'), findsOneWidget);
    expect(find.text('改为审批'), findsOneWidget);
    expect(find.text('编辑定义'), findsOneWidget);
  });

  testWidgets('ControlTaskBoard renders error banner and retry action', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: ControlTaskBoard(
            tasks: const [],
            isLoading: false,
            errorMessage: '加载规划任务失败',
            onRetry: _noop,
            onRunTask: _onRun,
            isTaskRunning: (_) => false,
            onToggleTask: _onRun,
            isTaskUpdating: (_) => false,
            onToggleApproval: _onRun,
            onEditDefinition: _onRun,
          ),
        ),
      ),
    );

    expect(find.text('加载规划任务失败'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
  });
}

void _noop() {}
void _onRun(ControlTaskRecord _) {}
