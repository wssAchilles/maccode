import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/widgets/rag/rag_input_area.dart';

void main() {
  testWidgets('RagInputArea disables send for empty input', (tester) async {
    var sent = 0;
    final controller = TextEditingController();
    addTearDown(controller.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RagInputArea(
            controller: controller,
            isLoading: false,
            onSend: () => sent += 1,
          ),
        ),
      ),
    );

    expect(
      tester
          .widget<IconButton>(find.byKey(const ValueKey('rag-send-button')))
          .onPressed,
      isNull,
    );

    await tester.enterText(
      find.byKey(const ValueKey('rag-input-field')),
      'hello',
    );
    await tester.pump();

    expect(
      tester
          .widget<IconButton>(find.byKey(const ValueKey('rag-send-button')))
          .onPressed,
      isNotNull,
    );
    await tester.tap(find.byKey(const ValueKey('rag-send-button')));
    expect(sent, 1);
  });
}
