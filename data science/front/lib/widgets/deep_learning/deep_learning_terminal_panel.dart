/// 深度学习页面训练日志终端组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/animated_glass_card.dart';

class DeepLearningTerminalPanel extends StatelessWidget {
  const DeepLearningTerminalPanel({
    super.key,
    required this.isTraining,
    required this.logs,
  });

  final bool isTraining;
  final String logs;

  @override
  Widget build(BuildContext context) {
    final hasLogs = logs.trim().isNotEmpty;
    return AnimatedGlassCard(
      padding: EdgeInsets.zero,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: isTraining,
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          childrenPadding: EdgeInsets.zero,
          leading: const Icon(
            Icons.terminal_rounded,
            size: 20,
            color: AppColors.textSecondary,
          ),
          title: Text('实时日志', style: AppTextStyles.labelLarge),
          subtitle: Text(
            isTraining
                ? '训练运行中，展开查看最新事件。'
                : hasLogs
                ? '日志已收起，展开查看训练事件。'
                : '等待训练任务。',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodySmall,
          ),
          trailing: isTraining
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.expand_more_rounded),
          children: [
            Container(
              key: const ValueKey('deep-learning-terminal'),
              height: 260,
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: const Color(0xFF1E293B),
              child: SingleChildScrollView(
                reverse: true,
                child: Text(
                  hasLogs ? logs : '等待训练任务...',
                  style: AppTextStyles.codeFont.copyWith(
                    color: const Color(0xFF34D399),
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
