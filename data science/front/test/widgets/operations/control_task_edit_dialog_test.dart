import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/control_task_record.dart';
import 'package:front/models/control_task_schedule_draft.dart';
import 'package:front/widgets/operations/control_task_edit_dialog.dart';

void main() {
  testWidgets('control task edit dialog returns parsed definition draft', (
    tester,
  ) async {
    ControlTaskDefinitionDraft? draft;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) {
              return TextButton(
                onPressed: () async {
                  draft = await showControlTaskEditDialog(
                    context,
                    const ControlTaskRecord(
                      id: 'train_model_daily',
                      kind: 'scheduler',
                      operationType: 'train_model',
                      title: '每日模型重训',
                      schedule: 'every day 04:00 UTC',
                      dependencies: ['dataset_ready'],
                      approvalPolicy: {'required': false, 'mode': 'auto'},
                      owner: 'system',
                      defaultInput: {'window_days': 30},
                    ),
                  );
                },
                child: const Text('open'),
              );
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    await tester.enterText(_fieldByLabel('每日执行时间'), '05:00');
    await tester.enterText(_fieldByLabel('责任人'), 'mlops');
    await tester.enterText(
      _fieldByLabel('依赖列表'),
      'dataset_ready, weather_ready',
    );
    await tester.ensureVisible(find.byType(Switch));
    await tester.tap(find.byType(Switch), warnIfMissed: false);
    await tester.pumpAndSettle();
    await tester.enterText(_fieldByLabel('审批原因'), '高成本重训需要审批');
    await tester.ensureVisible(_fieldByLabel('默认输入 JSON'));
    await tester.enterText(
      _fieldByLabel('默认输入 JSON'),
      '{"window_days":60,"retrain":true}',
    );

    await tester.tap(find.text('保存'));
    await tester.pumpAndSettle();

    expect(draft, isNotNull);
    expect(draft!.schedule, 'every day 05:00 UTC');
    expect(draft!.owner, 'mlops');
    expect(draft!.dependencies, ['dataset_ready', 'weather_ready']);
    expect(draft!.approvalPolicy['required'], isTrue);
    expect(draft!.approvalPolicy['reason'], '高成本重训需要审批');
    expect(draft!.defaultInput['window_days'], 60);
    expect(draft!.defaultInput['retrain'], isTrue);
  });

  testWidgets(
    'control task edit dialog disables save when schedule is invalid',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) {
                return TextButton(
                  onPressed: () async {
                    await showControlTaskEditDialog(
                      context,
                      const ControlTaskRecord(
                        id: 'train_model_daily',
                        kind: 'scheduler',
                        operationType: 'train_model',
                        title: '每日模型重训',
                        owner: 'system',
                      ),
                    );
                  },
                  child: const Text('open'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      await tester.tap(
        find.byType(DropdownButtonFormField<ControlTaskScheduleMode>),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('按小时').last);
      await tester.pumpAndSettle();

      await tester.enterText(_fieldByLabel('每隔多少小时'), '0');
      await tester.pumpAndSettle();

      final saveButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, '保存'),
      );
      expect(saveButton.onPressed, isNull);
      expect(find.textContaining('大于 0 的整数'), findsOneWidget);
    },
  );
}

Finder _fieldByLabel(String labelText) {
  return find.byWidgetPredicate(
    (widget) =>
        widget is TextField && widget.decoration?.labelText == labelText,
  );
}
