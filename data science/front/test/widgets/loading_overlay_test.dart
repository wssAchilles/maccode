import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/loading_overlay.dart';

void main() {
  testWidgets('LoadingOverlay exposes semantics and blocks child taps', (
    tester,
  ) async {
    var taps = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LoadingOverlay(
            isLoading: true,
            message: '同步中',
            child: TextButton(
              onPressed: () => taps += 1,
              child: const Text('底层按钮'),
            ),
          ),
        ),
      ),
    );

    expect(find.text('同步中'), findsOneWidget);
    expect(find.bySemanticsLabel('同步中'), findsWidgets);

    await tester.tap(find.text('底层按钮'), warnIfMissed: false);
    expect(taps, 0);
  });
}
