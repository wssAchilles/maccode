/// Compute governance summary card for rollout change operations.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';

class OperationComputeGovernanceSummary extends StatelessWidget {
  const OperationComputeGovernanceSummary({
    super.key,
    required this.operation,
  });

  final JobRecord operation;

  @override
  Widget build(BuildContext context) {
    if (operation.type != 'compute_rollout_change') {
      return const SizedBox.shrink();
    }

    final result = operation.result;
    final beforePolicy = result['before_policy'];
    final afterPolicy = result['after_policy'];
    if (beforePolicy is! Map || afterPolicy is! Map) {
      return const SizedBox.shrink();
    }

    final before = Map<String, dynamic>.from(beforePolicy);
    final after = Map<String, dynamic>.from(afterPolicy);
    final rollbackPatch = result['rollback_patch'];
    final rollback = rollbackPatch is Map
        ? Map<String, dynamic>.from(rollbackPatch)
        : const <String, dynamic>{};
    final beforeStatus = result['before_component_status'];
    final afterStatus = result['after_component_status'];
    final beforeStatusMap = beforeStatus is Map
        ? Map<String, dynamic>.from(beforeStatus)
        : const <String, dynamic>{};
    final afterStatusMap = afterStatus is Map
        ? Map<String, dynamic>.from(afterStatus)
        : const <String, dynamic>{};
    final requestKind = (result['request_kind'] ?? '').toString();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('治理变更摘要', style: AppTextStyles.labelLarge),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _Chip(
                label:
                    '组件 · ${(result['component_label'] ?? result['component'] ?? '--').toString()}',
              ),
              _Chip(
                label:
                    'Before · ${_rolloutLabel((before['rollout_mode'] ?? '').toString())}',
              ),
              _Chip(
                label:
                    'After · ${_rolloutLabel((after['rollout_mode'] ?? '').toString())}',
              ),
              _Chip(
                label:
                    'Canary · ${(after['canary_percent'] ?? 0).toString()}%',
              ),
              if (requestKind.isNotEmpty)
                _Chip(
                  label: requestKind == 'rollback' ? '请求 · 回退' : '请求 · 治理变更',
                ),
              if ((afterStatusMap['rollout_status'] ?? '').toString().isNotEmpty)
                _Chip(
                  label:
                      '状态 · ${_runtimeLabel((afterStatusMap['rollout_status'] ?? '').toString())}',
                ),
            ],
          ),
          if ((result['change_reason'] ?? '').toString().trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '变更说明 · ${(result['change_reason'] ?? '').toString()}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (rollback.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '回退目标 · ${_rolloutLabel((rollback['rollout_mode'] ?? '').toString())}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ],
          if ((beforeStatusMap['rollout_blocker'] ?? '').toString().trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '变更前阻塞 · ${(beforeStatusMap['rollout_blocker'] ?? '').toString()}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.warning,
              ),
            ),
          ],
          if ((afterStatusMap['last_auto_rollback_reason'] ?? '').toString().trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '自动回退记录 · ${(afterStatusMap['last_auto_rollback_reason'] ?? '').toString()}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.warning,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(label, style: AppTextStyles.bodySmall),
    );
  }
}

String _rolloutLabel(String mode) {
  switch (mode) {
    case 'python_stable':
      return '稳定 Python';
    case 'native_candidate':
      return '灰度 Native';
    case 'native_enforced':
      return '强制 Native';
    case 'python_loop':
      return '逐场景循环';
    case 'vectorized_python':
      return '向量化';
    default:
      return mode.isEmpty ? '--' : mode;
  }
}

String _runtimeLabel(String status) {
  switch (status) {
    case 'benchmark_pending':
      return 'Benchmark Pending';
    case 'blocked':
      return 'Blocked';
    case 'native_enforced':
      return 'Native Forced';
    case 'canary_ready':
      return 'Canary Ready';
    case 'auto_rolled_back':
      return 'Auto Rolled Back';
    case 'vectorized_active':
      return 'Vectorized';
    case 'loop_pinned':
      return 'Loop Pinned';
    default:
      return status.isEmpty ? '--' : status;
  }
}
