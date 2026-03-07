/// RAG 对话气泡组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/rag_message.dart';
import '../common/animated_glass_card.dart';

class RagMessageBubble extends StatelessWidget {
  const RagMessageBubble({
    super.key,
    required this.message,
  });

  final RagMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final isError = message.isError;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            AnimatedGlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              gradientBorder: isUser
                  ? null
                  : (isError ? null : AppColors.ragGradient),
              margin: const EdgeInsets.only(bottom: 8),
              child: SelectableText(
                message.content,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: isError ? AppColors.error : AppColors.textPrimary,
                ),
              ),
            ),
            if (!isUser && message.sources != null && message.sources!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(left: 8, bottom: 16),
                child: Wrap(
                  spacing: 8,
                  children: message.sources!.take(2).map((source) {
                    return Chip(
                      label: Text('Source: ${_sourcePreview(source)}'),
                      backgroundColor: AppColors.surfaceVariant,
                      labelStyle: AppTextStyles.labelSmall,
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

  String _sourcePreview(dynamic source) {
    final preview = source.toString();
    if (preview.length <= 20) {
      return preview;
    }
    return '${preview.substring(0, 20)}...';
  }
}
