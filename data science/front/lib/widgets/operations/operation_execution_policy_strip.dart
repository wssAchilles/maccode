/// Execution-policy metadata strip for operation console.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';

class OperationExecutionPolicyStrip extends StatelessWidget {
  const OperationExecutionPolicyStrip({
    super.key,
    required this.operation,
  });

  final JobRecord operation;

  @override
  Widget build(BuildContext context) {
    final step = operation.currentStep;
    if (step == null) {
      return const SizedBox.shrink();
    }

    final chips = <String>[
      if ((step.executionTarget ?? '').isNotEmpty)
        '执行平面 · ${step.executionTarget}',
      if (step.timeoutS != null) '超时 · ${step.timeoutS}s',
      if ((step.concurrencyKey ?? '').isNotEmpty)
        '并发键 · ${step.concurrencyKey}',
      if ((step.retryPolicy?['max_attempts']) != null)
        '重试预算 · ${step.retryPolicy!['max_attempts']} 次',
      if (step.durationMs != null) '耗时 · ${step.durationMs} ms',
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
