/// RAG 页面 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/rag_message.dart';
import '../services/rag_gateway.dart';

class RagViewModel extends ChangeNotifier {
  RagViewModel({RagGateway? gateway}) : _gateway = gateway ?? ApiRagGateway();

  final RagGateway _gateway;

  List<RagMessage> _messages = const [];
  bool _isLoading = false;
  bool _isDisposed = false;

  List<RagMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;

  void clearMessages() {
    if (_messages.isEmpty || _isLoading) {
      return;
    }
    _messages = const [];
    _notifySafely();
  }

  Future<void> sendMessage(String rawText, {String? collectionName}) async {
    final text = rawText.trim();
    if (text.isEmpty || _isLoading) {
      return;
    }

    _messages = [..._messages, RagMessage(role: 'user', content: text)];
    _isLoading = true;
    _notifySafely();

    try {
      final result = await _gateway.askQuestion(
        question: text,
        collectionName: collectionName?.trim().isEmpty ?? true
            ? null
            : collectionName!.trim(),
      );
      final payload = _normalizeResult(result);
      final answer = (payload['answer'] ?? 'No answer found.').toString();
      final rawSources = payload['context'];
      final sources = rawSources is List<dynamic>
          ? rawSources
          : const <dynamic>[];

      _messages = [
        ..._messages,
        RagMessage(role: 'assistant', content: answer, sources: sources),
      ];
    } catch (e) {
      _messages = [
        ..._messages,
        RagMessage(role: 'error', content: e.toString()),
      ];
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  Map<String, dynamic> _normalizeResult(Map<String, dynamic> result) {
    final nested = result['result'];
    if (nested is Map<String, dynamic>) {
      return nested;
    }
    return result;
  }

  @override
  void dispose() {
    _isDisposed = true;
    super.dispose();
  }
}
