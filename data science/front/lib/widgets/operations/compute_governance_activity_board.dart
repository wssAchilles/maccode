/// Compute governance activity board.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/compute_governance_activity_entry.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ComputeGovernanceActivityBoard extends StatelessWidget {
  const ComputeGovernanceActivityBoard({
    super.key,
    required this.entries,
    required this.isLoading,
    this.onOpenOperation,
  });

  final List<ComputeGovernanceActivityEntry> entries;
  final bool isLoading;
  final ValueChanged<ComputeGovernanceActivityEntry>? onOpenOperation;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '治理审计',
      subtitle: '最近的 rollout、benchmark 和自动回退事件统一归档到控制面审计流。',
      child: GlassCard(
        padding: const EdgeInsets.all(16),
        child: entries.isEmpty
            ? Text(
                isLoading ? '正在加载治理审计流…' : '当前没有计算治理活动。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              )
            : Column(
                children: entries
                    .map(
                      (entry) => _ActivityTile(
                        entry: entry,
                        onOpenOperation: onOpenOperation,
                      ),
                    )
                    .toList(growable: false),
              ),
      ),
    );
  }
}

class _ActivityTile extends StatelessWidget {
  const _ActivityTile({
    required this.entry,
    this.onOpenOperation,
  });

  final ComputeGovernanceActivityEntry entry;
  final ValueChanged<ComputeGovernanceActivityEntry>? onOpenOperation;

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(entry);
    final canOpen = entry.hasLinkedOperation && onOpenOperation != null;
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tone.background.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: tone.foreground.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(entry.title, style: AppTextStyles.labelLarge),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _ActivityPill(
                          label: _kindLabel(entry),
                          foreground: tone.foreground,
                          background: Colors.white.withValues(alpha: 0.72),
                        ),
                        if (entry.status.trim().isNotEmpty)
                          _ActivityPill(
                            label: entry.status.toUpperCase(),
                            foreground: AppColors.textPrimary,
                            background: AppColors.surfaceVariant,
                          ),
                        if (entry.componentLabel.trim().isNotEmpty)
                          _ActivityPill(
                            label: entry.componentLabel,
                            foreground: AppColors.textPrimary,
                            background: AppColors.surfaceVariant,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              if (canOpen)
                TextButton.icon(
                  onPressed: () => onOpenOperation?.call(entry),
                  icon: const Icon(Icons.open_in_new_rounded),
                  label: const Text('查看运行'),
                ),
            ],
          ),
          if (entry.summary.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              entry.summary,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (entry.rolloutMode.trim().isNotEmpty)
                _InfoChip(label: 'Rollout', value: _rolloutLabel(entry.rolloutMode)),
              if (entry.benchmarkStatus.trim().isNotEmpty)
                _InfoChip(label: 'Benchmark', value: entry.benchmarkStatus),
              if (entry.operationId.trim().isNotEmpty)
                _InfoChip(label: 'Operation', value: entry.operationId),
              if (entry.createdAt.trim().isNotEmpty)
                _InfoChip(
                  label: '时间',
                  value: entry.createdAt.contains('T')
                      ? entry.createdAt.split('T').first
                      : entry.createdAt,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

({Color foreground, Color background}) _toneFor(
  ComputeGovernanceActivityEntry entry,
) {
  final status = entry.status.toLowerCase();
  final severity = entry.severity.toLowerCase();
  if (status == 'failed' || severity == 'error') {
    return (
      foreground: AppColors.error,
      background: AppColors.errorLight,
    );
  }
  if (severity == 'warning' || status == 'awaiting_approval') {
    return (
      foreground: AppColors.warning,
      background: AppColors.warningLight,
    );
  }
  return (
    foreground: AppColors.success,
    background: AppColors.successLight,
  );
}

String _kindLabel(ComputeGovernanceActivityEntry entry) {
  if (entry.kind == 'system_event') {
    return 'System Event';
  }
  if (entry.operationType == 'compute_benchmark') {
    return 'Benchmark';
  }
  return entry.requestKind == 'rollback' ? 'Rollback' : 'Rollout';
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
      return mode;
  }
}

class _ActivityPill extends StatelessWidget {
  const _ActivityPill({
    required this.label,
    required this.foreground,
    required this.background,
  });

  final String label;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.bodySmall.copyWith(color: foreground),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textPrimary),
      ),
    );
  }
}
