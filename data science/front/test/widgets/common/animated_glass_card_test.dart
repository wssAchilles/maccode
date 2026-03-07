import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/common/animated_glass_card.dart';

void main() {
  testWidgets('AnimatedGlassCard applies margin and handles tap', (
    WidgetTester tester,
  ) async {
    var tapCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AnimatedGlassCard(
            margin: const EdgeInsets.all(12),
            onTap: () => tapCount += 1,
            child: const Text('Animated card'),
          ),
        ),
      ),
    );

    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Container && widget.margin == const EdgeInsets.all(12),
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Animated card'));
    await tester.pumpAndSettle();

    expect(tapCount, 1);
  });
}
