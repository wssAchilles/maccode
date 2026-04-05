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
    required this.onRequestRolloutMode,
    required this.onRunBenchmark,
  });

  final ComputeRolloutPolicy policy;
  final bool isLoading;
  final bool Function(String componentKey) isUpdatingComponent;
  final void Function(
    ComputeRolloutComponentPolicy component,
    String rolloutMode,
  )
  onRequestRolloutMode;
  final ValueChanged<ComputeRolloutComponentPolicy> onRunBenchmark;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '计算治理',
      subtitle: '对热点组件的 backend rollout 提交治理运行，统一走审批、审计和回退链。',
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
                  label:
                      'UPDATED · ${policy.updatedAt.isEmpty ? "--" : "LIVE"}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label:
                      'OWNER · ${policy.updatedBy.isEmpty ? "--" : policy.updatedBy}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                if (policy.guardEnabled)
                  _Pill(
                    label:
                        'GUARD · ${policy.guardFailureThreshold}/${policy.guardWindowMinutes}m',
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
                        onRequestRolloutMode: onRequestRolloutMode,
                        onRunBenchmark: onRunBenchmark,
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
    required this.onRequestRolloutMode,
    required this.onRunBenchmark,
  });

  final ComputeRolloutComponentPolicy component;
  final bool isUpdating;
  final void Function(
    ComputeRolloutComponentPolicy component,
    String rolloutMode,
  )
  onRequestRolloutMode;
  final ValueChanged<ComputeRolloutComponentPolicy> onRunBenchmark;

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
                value: _benchmarkGateLabel(component),
              ),
              _InfoChip(label: 'Canary', value: '${component.canaryPercent}%'),
              _InfoChip(
                label: 'Runtime',
                value: _rolloutRuntimeLabel(component.rolloutStatus),
              ),
              if (component.guardEnabled)
                _InfoChip(
                  label: 'Guard',
                  value:
                      '${component.recentFailureCount}/${component.guardFailureThreshold}',
                ),
            ],
          ),
          if (component.runtimeTargets.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: component.runtimeTargets
                  .map(
                    (target) => _InfoChip(
                      label: target.workerLabel,
                      value: _runtimeTargetLabel(target),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
          if (component.lastBenchmarkContext.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '最近 benchmark: ${component.lastBenchmarkContext}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (component.benchmarkSummary.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              component.benchmarkSummary,
              style: AppTextStyles.bodySmall.copyWith(
                color: component.benchmarkPassed
                    ? AppColors.success
                    : AppColors.textSecondary,
              ),
            ),
          ],
          if (component.benchmarkSpeedupRatio != null) ...[
            const SizedBox(height: 6),
            Text(
              '速度比 ${component.benchmarkSpeedupRatio!.toStringAsFixed(2)}x / 阈值 ${component.benchmarkThreshold.toStringAsFixed(2)}x · 样本 ${component.benchmarkSampleRows}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ],
          if (component.rolloutBlocker.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              component.rolloutBlocker,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.warning),
            ),
          ],
          if (component.lastAutoRollbackReason.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '自动回退 · ${component.lastAutoRollbackReason}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.warning,
              ),
            ),
          ],
          if (component.lastFailureReason.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '最近失败 · ${component.lastFailureReason}',
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
            children: [
              FilledButton.tonalIcon(
                onPressed: isUpdating ? null : () => onRunBenchmark(component),
                icon: const Icon(Icons.speed_rounded),
                label: const Text('运行 Benchmark'),
              ),
              ...component.allowedModes.map(
                (mode) => OutlinedButton(
                  onPressed: _canRequestRolloutMode(component, mode, isUpdating)
                      ? () => onRequestRolloutMode(component, mode)
                      : null,
                  child: Text(_rolloutActionLabel(component, mode)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

bool _canRequestRolloutMode(
  ComputeRolloutComponentPolicy component,
  String mode,
  bool isUpdating,
) {
  if (isUpdating) {
    return false;
  }

  final isCanaryAdjustment =
      component.key == 'feature_engineering' &&
      mode == 'native_candidate' &&
      component.rolloutMode == 'native_candidate';
  if (mode == component.rolloutMode && !isCanaryAdjustment) {
    return false;
  }

  if (component.key == 'feature_engineering' &&
      (mode == 'native_candidate' || mode == 'native_enforced')) {
    return component.benchmarkReady && component.nativeReadyTargets.isNotEmpty;
  }
  return true;
}

String _benchmarkGateLabel(ComputeRolloutComponentPolicy component) {
  switch (component.benchmarkStatus) {
    case 'passed':
      return 'Passed';
    case 'failed':
      return 'Failed';
    case 'stale':
      return 'Stale';
    case 'recorded':
      return 'Recorded';
    default:
      return 'Pending';
  }
}

String _rolloutActionLabel(
  ComputeRolloutComponentPolicy component,
  String mode,
) {
  if (component.key == 'feature_engineering' &&
      mode == 'native_candidate' &&
      component.rolloutMode == 'native_candidate') {
    return '调整灰度';
  }
  if (mode == 'python_stable' && component.rolloutMode != 'python_stable') {
    return '回退稳定';
  }
  return _rolloutLabel(mode);
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
      child: Text('$label · $value', style: AppTextStyles.bodySmall),
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

String _rolloutRuntimeLabel(String status) {
  switch (status) {
    case 'benchmark_pending':
      return 'Benchmark Pending';
    case 'benchmark_recorded':
      return 'Benchmark Recorded';
    case 'benchmark_failed':
      return 'Benchmark Failed';
    case 'benchmark_stale':
      return 'Benchmark Stale';
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
      return 'Stable';
  }
}

String _runtimeTargetLabel(ComputeRuntimeTargetStatus target) {
  if (!target.configured) {
    return 'Unconfigured';
  }
  if (!target.reachable) {
    return 'Unreachable';
  }
  if (target.nativeEnabled && target.nativeAvailable) {
    return 'Native Ready';
  }
  if (target.nativeEnabled) {
    return 'Native Missing';
  }
  return 'Python';
}

class _ModeTone {
  const _ModeTone(this.foreground, this.background);

  final Color foreground;
  final Color background;
}
