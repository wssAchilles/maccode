import 'package:flutter/material.dart';
import '../config/app_theme.dart';
import '../services/api_service.dart';
import '../widgets/common/animated_glass_card.dart';
import '../widgets/responsive_wrapper.dart';

class RagScreen extends StatefulWidget {
  const RagScreen({super.key});

  @override
  State<RagScreen> createState() => _RagScreenState();
}

class _RagScreenState extends State<RagScreen> {
  final _controller = TextEditingController();
  final List<Message> _messages = [];
  bool _isLoading = false;

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add(Message(role: 'user', content: text));
      _isLoading = true;
    });
    _controller.clear();

    try {
      final result = await ApiService.askRagQuestion(question: text);
      final answer = result['answer'] ?? 'No answer found.';
      final context = result['context'] as List<dynamic>?;

      setState(() {
        _messages.add(Message(
          role: 'assistant',
          content: answer,
          sources: context,
        ));
      });
    } catch (e) {
      setState(() {
        _messages.add(Message(
          role: 'error',
          content: 'Error: $e',
        ));
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('知识库助手 (RAG)'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        flexibleSpace: Opacity(
          opacity: 0.8,
          child: Container(
            decoration: const BoxDecoration(
              gradient: AppColors.ragGradient,
            ),
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppColors.backgroundGradient,
        ),
        child: SafeArea(
          child: ResponsiveWrapper(
            child: Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(20),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      return _buildMessage(_messages[index]);
                    },
                  ),
                ),
                _buildInputArea(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMessage(Message msg) {
    final isUser = msg.role == 'user';
    final isError = msg.role == 'error';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            AnimatedGlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              gradientBorder: isUser 
                  ? null 
                  : (isError ? null : AppColors.ragGradient),
              margin: const EdgeInsets.only(bottom: 8),
              child: SelectableText( // Copyable text
                msg.content,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: isError ? AppColors.error : AppColors.textPrimary,
                ),
              ),
            ),
            if (!isUser && msg.sources != null && msg.sources!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(left: 8, bottom: 16),
                child: Wrap(
                  spacing: 8,
                  children: msg.sources!.take(2).map((s) { // 只显示前2个来源
                     // 简单解析，假设 context 是 list of strings
                     String preview = s.toString();
                     if (preview.length > 20) preview = '${preview.substring(0, 20)}...';
                     return Chip(
                       label: Text('Source: $preview'),
                       backgroundColor: AppColors.surfaceVariant,
                       labelStyle: AppTextStyles.labelSmall, // 需添加或使用 bodySmall
                       visualDensity: VisualDensity.compact,
                     );
                  }).toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputArea() {
    return AnimatedGlassCard(
      margin: const EdgeInsets.all(20),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      borderRadius: 30, // Capsule shape
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: 'Ask anything about your documents...',
                border: InputBorder.none,
                focusedBorder: InputBorder.none,
                enabledBorder: InputBorder.none,
                fillColor: Colors.transparent,
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          IconButton(
            onPressed: _isLoading ? null : _sendMessage,
            icon: _isLoading 
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.send_rounded, color: Color(0xFF0EA5E9)),
          ),
        ],
      ),
    );
  }
}

class Message {
  final String role;
  final String content;
  final List<dynamic>? sources;

  Message({required this.role, required this.content, this.sources});
}
