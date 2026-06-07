/// RAG 输入区组件
library;

import 'package:flutter/material.dart';

import '../common/animated_glass_card.dart';

class RagInputArea extends StatelessWidget {
  const RagInputArea({
    super.key,
    required this.controller,
    required this.isLoading,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      margin: const EdgeInsets.all(20),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      borderRadius: 30,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              key: const ValueKey('rag-input-field'),
              controller: controller,
              enabled: !isLoading,
              decoration: const InputDecoration(
                labelText: 'RAG 问题',
                hintText: '询问文档摘要、出处定位或关键对比...',
                helperText: '输入问题后发送，空问题不会提交。',
                border: InputBorder.none,
                focusedBorder: InputBorder.none,
                enabledBorder: InputBorder.none,
                fillColor: Colors.transparent,
              ),
              onSubmitted: (_) {
                final canSend = !isLoading && controller.text.trim().isNotEmpty;
                if (canSend) {
                  onSend();
                }
              },
            ),
          ),
          ValueListenableBuilder<TextEditingValue>(
            valueListenable: controller,
            builder: (context, value, _) {
              final canSend = !isLoading && value.text.trim().isNotEmpty;
              return IconButton(
                key: const ValueKey('rag-send-button'),
                tooltip: canSend ? '发送问题' : '请输入问题后发送',
                onPressed: canSend ? onSend : null,
                icon: isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send_rounded, color: Color(0xFF0EA5E9)),
              );
            },
          ),
        ],
      ),
    );
  }
}
