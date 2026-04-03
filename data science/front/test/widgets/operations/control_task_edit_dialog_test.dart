import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/control_task_record.dart';
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

    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'every day 05:00 UTC');
    await tester.enterText(fields.at(1), 'mlops');
    await tester.enterText(fields.at(2), 'dataset_ready, weather_ready');
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    await tester.enterText(fields.at(3), '高成本重训需要审批');
    await tester.enterText(fields.at(4), '{"window_days":60,"retrain":true}');

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

      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), 'daily at 5');
      await tester.pumpAndSettle();

      final saveButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, '保存'),
      );
      expect(saveButton.onPressed, isNull);
      expect(find.textContaining('every N hours'), findsOneWidget);
    },
  );
}
