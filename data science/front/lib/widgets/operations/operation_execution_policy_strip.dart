/// Execution-policy metadata strip for operation console.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';

class OperationExecutionPolicyStrip extends StatelessWidget {
  const OperationExecutionPolicyStrip({super.key, required this.operation});

  final JobRecord operation;

  @override
  Widget build(BuildContext context) {
    final step = operation.currentStep;
    final stepExecutionTarget = step?.executionTarget ?? '';
    final stepTimeout = step?.timeoutS;
    final stepConcurrencyKey = step?.concurrencyKey ?? '';
    final stepRetryAttempts = step?.retryPolicy?['max_attempts'];
    final stepDuration = step?.durationMs;

    if (step == null && (operation.executionTarget ?? '').isEmpty) {
      return const SizedBox.shrink();
    }

    final chips = <String>[
      if ((operation.executionTarget ?? '').isNotEmpty)
        '运行目标 · ${operation.executionTarget}',
      if (stepExecutionTarget.isNotEmpty) '执行平面 · $stepExecutionTarget',
      if (stepTimeout != null) '超时 · ${stepTimeout}s',
      if (stepConcurrencyKey.isNotEmpty) '并发键 · $stepConcurrencyKey',
      if (stepRetryAttempts != null) '重试预算 · $stepRetryAttempts 次',
      if (stepDuration != null) '耗时 · $stepDuration ms',
    ];

    if (chips.isEmpty) {
      return const SizedBox.shrink();
    }

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: chips
          .map(
            (item) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
              ),
              child: Text(
                item,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}
