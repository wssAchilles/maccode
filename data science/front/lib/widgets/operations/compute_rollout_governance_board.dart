/// Compute rollout governance board.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/compute_rollout_policy.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ComputeRolloutGovernanceBoard extends StatelessWidget {
  const ComputeRolloutGovernanceBoard({
    super.key,
    required this.policy,
    required this.isLoading,
    required this.isUpdatingComponent,
    required this.onSetRolloutMode,
  });

  final ComputeRolloutPolicy policy;
  final bool isLoading;
  final bool Function(String componentKey) isUpdatingComponent;
  final void Function(ComputeRolloutComponentPolicy component, String rolloutMode)
  onSetRolloutMode;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '计算治理',
      subtitle: '对热点组件的 backend rollout 做受控切换，而不是直接改运行代码路径。',
      child: GlassCard(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _Pill(
                  label: policy.enabled ? 'ROLLOUT ON' : 'ROLLOUT OFF',
                  foreground: policy.enabled
                      ? AppColors.success
                      : AppColors.warning,
                  background: policy.enabled
                      ? AppColors.successLight
                      : AppColors.warningLight,
                ),
                _Pill(
                  label: 'UPDATED · ${policy.updatedAt.isEmpty ? "--" : "LIVE"}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label: 'OWNER · ${policy.updatedBy.isEmpty ? "--" : policy.updatedBy}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
              ],
            ),
            const SizedBox(height: 14),
            if (policy.components.isEmpty)
              Text(
                isLoading ? '正在加载治理策略…' : '当前没有可治理的计算组件。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              )
            else
              Column(
                children: policy.components
                    .map(
                      (component) => _ComponentPolicyCard(
                        component: component,
                        isUpdating: isUpdatingComponent(component.key),
                        onSetRolloutMode: onSetRolloutMode,
                      ),
                    )
                    .toList(growable: false),
              ),
          ],
        ),
      ),
    );
  }
}

class _ComponentPolicyCard extends StatelessWidget {
  const _ComponentPolicyCard({
    required this.component,
    required this.isUpdating,
    required this.onSetRolloutMode,
  });

  final ComputeRolloutComponentPolicy component;
  final bool isUpdating;
  final void Function(ComputeRolloutComponentPolicy component, String rolloutMode)
  onSetRolloutMode;

  @override
  Widget build(BuildContext context) {
    final modeTone = _modeTone(component.rolloutMode);
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: modeTone.background.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: modeTone.foreground.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(component.label, style: AppTextStyles.labelLarge),
              ),
              if (isUpdating)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                _Pill(
                  label: _rolloutLabel(component.rolloutMode),
                  foreground: modeTone.foreground,
                  background: Colors.white.withValues(alpha: 0.62),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _InfoChip(label: 'Backend', value: component.preferredBackend),
              _InfoChip(
                label: 'Benchmark',
                value: component.benchmarkReady ? 'Ready' : 'Pending',
              ),
              _InfoChip(
                label: 'Canary',
                value: '${component.canaryPercent}%',
              ),
            ],
          ),
          if (component.lastBenchmarkContext.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '最近 benchmark: ${component.lastBenchmarkContext}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (component.notes.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              component.notes,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: component.allowedModes
                .map(
                  (mode) => OutlinedButton(
                    onPressed: isUpdating || mode == component.rolloutMode
                        ? null
                        : () => onSetRolloutMode(component, mode),
                    child: Text(_rolloutLabel(mode)),
                  ),
                )
                .toList(growable: false),
          ),
        ],
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
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.bodySmall,
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
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
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(color: foreground),
      ),
    );
  }
}

_ModeTone _modeTone(String mode) {
  switch (mode) {
    case 'native_candidate':
      return const _ModeTone(AppColors.warning, AppColors.warningLight);
    case 'native_enforced':
      return const _ModeTone(AppColors.error, AppColors.errorLight);
    case 'vectorized_python':
      return const _ModeTone(AppColors.info, AppColors.infoLight);
    default:
      return const _ModeTone(AppColors.success, AppColors.successLight);
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
      return mode;
  }
}

class _ModeTone {
  const _ModeTone(this.foreground, this.background);

  final Color foreground;
  final Color background;
}
