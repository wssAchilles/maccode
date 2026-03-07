/// RAG 对话消息模型
library;

class RagMessage {
  const RagMessage({required this.role, required this.content, this.sources});

  final String role;
  final String content;
  final List<dynamic>? sources;

  bool get isUser => role == 'user';
  bool get isError => role == 'error';
}
