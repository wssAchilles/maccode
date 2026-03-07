/// RAG 会话列表组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/rag_message.dart';
import 'rag_message_bubble.dart';

class RagMessageList extends StatelessWidget {
  const RagMessageList({
    super.key,
    required this.messages,
    required this.scrollController,
  });

  final List<RagMessage> messages;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context) {
    if (messages.isEmpty) {
      return const _RagEmptyState();
    }

    return ListView.builder(
      key: const ValueKey('rag-message-list'),
      controller: scrollController,
      padding: const EdgeInsets.all(20),
      itemCount: messages.length,
      itemBuilder: (context, index) {
        return RagMessageBubble(message: messages[index]);
      },
    );
  }
}

class _RagEmptyState extends StatelessWidget {
  const _RagEmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          key: const ValueKey('rag-empty-state'),
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: AppColors.ragGradient,
                borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
              ),
              child: const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
                size: 32,
              ),
            ),
            const SizedBox(height: 16),
            Text('开始新的知识库对话', style: AppTextStyles.h3),
            const SizedBox(height: 8),
            Text(
              '询问文档内容、总结、对比或定位关键片段。',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
