import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'package:front/services/rag_gateway.dart';
import 'package:front/viewmodels/rag_view_model.dart';

class _FakeRagGateway implements RagGateway {
  Map<String, dynamic> response = const {
    'answer': 'default',
    'context': <dynamic>[],
  };
  Object? error;
  Completer<Map<String, dynamic>>? completer;
  String? lastQuestion;
  String? lastCollectionName;

  @override
  Future<Map<String, dynamic>> askQuestion({
    required String question,
    String? collectionName,
  }) async {
    lastQuestion = question;
    lastCollectionName = collectionName;

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

void main() {
  test('sendMessage ignores blank input', () async {
    final gateway = _FakeRagGateway();
    final viewModel = RagViewModel(gateway: gateway);

    await viewModel.sendMessage('   ');

    expect(viewModel.messages, isEmpty);
    expect(gateway.lastQuestion, isNull);

    viewModel.dispose();
  });

  test('sendMessage appends user and assistant messages on success', () async {
    final gateway = _FakeRagGateway()
      ..response = const {
        'answer': '42',
        'context': ['doc-a', 'doc-b'],
      };
    final viewModel = RagViewModel(gateway: gateway);

    await viewModel.sendMessage('What is the answer?');

    expect(gateway.lastQuestion, 'What is the answer?');
    expect(viewModel.messages.length, 2);
    expect(viewModel.messages[0].role, 'user');
    expect(viewModel.messages[0].content, 'What is the answer?');
    expect(viewModel.messages[1].role, 'assistant');
    expect(viewModel.messages[1].content, '42');
    expect(viewModel.messages[1].sources, ['doc-a', 'doc-b']);
    expect(viewModel.isLoading, isFalse);

    viewModel.dispose();
  });

  test('sendMessage passes collection name through to gateway', () async {
    final gateway = _FakeRagGateway();
    final viewModel = RagViewModel(gateway: gateway);

    await viewModel.sendMessage(
      'What is the answer?',
      collectionName: 'ops-knowledge',
    );

    expect(gateway.lastQuestion, 'What is the answer?');
    expect(gateway.lastCollectionName, 'ops-knowledge');

    viewModel.dispose();
  });

  test('sendMessage appends error message on failure', () async {
    final gateway = _FakeRagGateway()..error = Exception('network');
    final viewModel = RagViewModel(gateway: gateway);

    await viewModel.sendMessage('hello');

    expect(viewModel.messages.length, 2);
    expect(viewModel.messages[0].role, 'user');
    expect(viewModel.messages[1].role, 'error');
    expect(viewModel.messages[1].content, contains('network'));
    expect(viewModel.isLoading, isFalse);

    viewModel.dispose();
  });

  test('sendMessage exposes loading while waiting for gateway', () async {
    final completer = Completer<Map<String, dynamic>>();
    final gateway = _FakeRagGateway()..completer = completer;
    final viewModel = RagViewModel(gateway: gateway);

    final pending = viewModel.sendMessage('in-flight');

    expect(viewModel.isLoading, isTrue);

    completer.complete(const {'answer': 'ok', 'context': []});
    await pending;

    expect(viewModel.isLoading, isFalse);
    expect(viewModel.messages.last.content, 'ok');

    viewModel.dispose();
  });
}
