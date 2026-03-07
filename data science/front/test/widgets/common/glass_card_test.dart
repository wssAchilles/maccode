import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/common/glass_card.dart';

void main() {
  testWidgets('GlassCard applies margin and handles tap', (
    WidgetTester tester,
  ) async {
    var tapCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: GlassCard(
            margin: const EdgeInsets.all(16),
            onTap: () => tapCount += 1,
            child: const Text('Glass content'),
          ),
        ),
      ),
    );

    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Container && widget.margin == const EdgeInsets.all(16),
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Glass content'));
    await tester.pump();

    expect(tapCount, 1);
  });

  testWidgets('DropZoneContainer forwards tap callback', (
    WidgetTester tester,
  ) async {
    var tapCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DropZoneContainer(
            isActive: true,
            onTap: () => tapCount += 1,
            child: const SizedBox(height: 80, child: Text('Upload zone')),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Upload zone'));
    await tester.pump();

    expect(tapCount, 1);
  });

  testWidgets('StatCard renders trend badge', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: StatCard(
            value: '98%',
            label: '准确率',
            trend: TrendDirection.up,
            trendValue: '+4%',
          ),
        ),
      ),
    );

    expect(find.text('98%'), findsOneWidget);
    expect(find.text('准确率'), findsOneWidget);
    expect(find.text('+4%'), findsOneWidget);
    expect(find.byIcon(Icons.trending_up_rounded), findsOneWidget);
  });
}
