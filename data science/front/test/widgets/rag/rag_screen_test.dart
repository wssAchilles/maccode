import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/screens/rag_screen.dart';
import 'package:front/services/rag_gateway.dart';
import 'package:front/viewmodels/rag_view_model.dart';

class _FakeRagGateway implements RagGateway {
  Map<String, dynamic> response = const {
    'answer': 'default answer',
    'context': <dynamic>[],
  };
  Object? error;
  Completer<Map<String, dynamic>>? completer;
  String? lastQuestion;

  @override
  Future<Map<String, dynamic>> askQuestion({required String question}) async {
    lastQuestion = question;

    final pending = completer;
    if (pending != null) {
      return pending.future;
    }

    if (error != null) {
      throw error!;
    }

    return response;
  }
}

Future<void> _pumpRagScreen(
  WidgetTester tester, {
  required RagViewModel viewModel,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: RagScreen(viewModel: viewModel),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('RagScreen shows empty state before any message is sent', (
    WidgetTester tester,
  ) async {
    final viewModel = RagViewModel(gateway: _FakeRagGateway());
    addTearDown(viewModel.dispose);

    await _pumpRagScreen(tester, viewModel: viewModel);

    expect(find.byKey(const ValueKey('rag-empty-state')), findsOneWidget);
    expect(find.text('开始新的知识库对话'), findsOneWidget);
  });

  testWidgets('RagScreen sends messages and renders assistant sources', (
    WidgetTester tester,
  ) async {
    final gateway = _FakeRagGateway()
      ..response = const {
        'answer': 'The answer is 42.',
        'context': ['doc-a', 'doc-b', 'doc-c'],
      };
    final viewModel = RagViewModel(gateway: gateway);
    addTearDown(viewModel.dispose);

    await _pumpRagScreen(tester, viewModel: viewModel);

    await tester.enterText(
      find.byKey(const ValueKey('rag-input-field')),
      'What is the answer?',
    );
    await tester.tap(find.byKey(const ValueKey('rag-send-button')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(gateway.lastQuestion, 'What is the answer?');
    expect(find.text('What is the answer?'), findsOneWidget);
    expect(find.text('The answer is 42.'), findsOneWidget);
    expect(find.text('Source: doc-a'), findsOneWidget);
    expect(find.text('Source: doc-b'), findsOneWidget);
  });

  testWidgets('RagScreen disables input while loading', (
    WidgetTester tester,
  ) async {
    final completer = Completer<Map<String, dynamic>>();
    final gateway = _FakeRagGateway()..completer = completer;
    final viewModel = RagViewModel(gateway: gateway);
    addTearDown(viewModel.dispose);

    await _pumpRagScreen(tester, viewModel: viewModel);

    await tester.enterText(
      find.byKey(const ValueKey('rag-input-field')),
      'pending request',
    );
    await tester.tap(find.byKey(const ValueKey('rag-send-button')));
    await tester.pump();

    final inputField = tester.widget<TextField>(
      find.byKey(const ValueKey('rag-input-field')),
    );
    expect(inputField.enabled, isFalse);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    completer.complete(const {'answer': 'ok', 'context': []});
    await tester.pumpAndSettle();
  });

  testWidgets('RagScreen renders error bubble on gateway failure', (
    WidgetTester tester,
  ) async {
    final viewModel = RagViewModel(
      gateway: _FakeRagGateway()..error = Exception('network down'),
    );
    addTearDown(viewModel.dispose);

    await _pumpRagScreen(tester, viewModel: viewModel);

    await tester.enterText(
      find.byKey(const ValueKey('rag-input-field')),
      'hello',
    );
    await tester.tap(find.byKey(const ValueKey('rag-send-button')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.textContaining('Error: Exception: network down'), findsOneWidget);
  });
}
