/// Compute acceleration telemetry board.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ComputeAccelerationBoard extends StatelessWidget {
  const ComputeAccelerationBoard({super.key, required this.status});

  final ComputeAccelerationStatus status;

  @override
  Widget build(BuildContext context) {
    final tone = _statusTone(status.status);
    return DutySectionBlock(
      title: '计算层',
      subtitle: '展示热点计算 profiling、Python fallback 与 C++ native backend 的接入准备度。',
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
                  label: status.enabled ? 'PROFILE ON' : 'PROFILE OFF',
                  foreground: tone.foreground,
                  background: tone.background,
                ),
                _Pill(
                  label: 'ACTIVE · ${_backendLabel(status.activeBackend)}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label: 'HOTTEST · ${status.hottestComponent}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label: 'SAMPLES · ${status.profiledComponents}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                if (status.rollout.components.isNotEmpty)
                  _Pill(
                    label:
                        'ROLLOUT · ${_rolloutHeadline(status.rollout.components.first.rolloutMode)}',
                    foreground: AppColors.textPrimary,
                    background: AppColors.surfaceVariant,
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              status.message.isEmpty ? '计算层状态正常' : status.message,
              style: AppTextStyles.bodySmall.copyWith(color: tone.foreground),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _MetaCard(
                    label: 'Preferred',
                    value: _backendLabel(status.preferredBackend),
                    hint: status.nativeEnabled
                        ? 'native requested'
                        : 'python stable path',
                    accent: AppColors.info,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetaCard(
                    label: 'Native',
                    value: status.nativeAvailable ? 'Ready' : 'Fallback',
                    hint: status.nativeAvailable
                        ? 'module discovered'
                        : 'Python fallback active',
                    accent: status.nativeAvailable
                        ? AppColors.success
                        : AppColors.warning,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetaCard(
                    label: 'Benchmark',
                    value: status.benchmarkReady ? 'Primed' : 'Pending',
                    hint: status.lastUpdatedAt.isEmpty
                        ? 'waiting for first sample'
                        : 'telemetry updated',
                    accent: status.benchmarkReady
                        ? AppColors.success
                        : AppColors.surfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            if (status.components.isEmpty)
              _EmptyState(message: '当前还没有热点样本，等下一次训练、取数或 benchmark 后这里会出现执行摘要。')
            else
              Column(
                children: status.components
                    .map((component) => _ComponentCard(component: component))
                    .toList(growable: false),
              ),
          ],
        ),
      ),
    );
  }
}

class _ComponentCard extends StatelessWidget {
  const _ComponentCard({required this.component});

  final ComputeAccelerationComponent component;

  @override
  Widget build(BuildContext context) {
    final tone = _statusTone(component.status);
    final normalized = (component.p95DurationMs / 450).clamp(0.0, 1.0);
    final contexts = component.contexts.isEmpty
        ? '--'
        : component.contexts.join(' / ');

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tone.background.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: tone.foreground.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(component.label, style: AppTextStyles.labelLarge),
              ),
              _Pill(
                label: _backendLabel(component.activeBackend),
                foreground: tone.foreground,
                background: Colors.white.withValues(alpha: 0.6),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _MetricLine(
                  label: 'Last',
                  value: '${component.lastDurationMs.toStringAsFixed(1)} ms',
                ),
              ),
              Expanded(
                child: _MetricLine(
                  label: 'Avg',
                  value: '${component.avgDurationMs.toStringAsFixed(1)} ms',
                ),
              ),
              Expanded(
                child: _MetricLine(
                  label: 'P95',
                  value: '${component.p95DurationMs.toStringAsFixed(1)} ms',
                ),
              ),
              Expanded(
                child: _MetricLine(
                  label: 'Rows',
                  value: '${component.lastRows}',
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: normalized,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            color: tone.foreground,
            backgroundColor: AppColors.surfaceVariant,
          ),
          const SizedBox(height: 10),
          Text(
            '场景: ${component.lastContext.isEmpty ? contexts : component.lastContext}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '建议: ${component.recommendedAction}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaCard extends StatelessWidget {
  const _MetaCard({
    required this.label,
    required this.value,
    required this.hint,
    required this.accent,
  });

  final String label;
  final String value;
  final String hint;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.labelMedium),
          const SizedBox(height: 8),
          Text(value, style: AppTextStyles.h4),
          const SizedBox(height: 6),
          Text(
            hint,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(value, style: AppTextStyles.labelLarge),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text(
        message,
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
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

String _backendLabel(String backend) {
  switch (backend) {
    case 'native_cpp':
      return 'Native C++';
    case 'python_vectorized':
      return 'Python Vectorized';
    case 'python_loop':
      return 'Python Loop';
    case 'python_numpy':
      return 'Python NumPy';
    default:
      return 'Python Pandas';
  }
}

_StatusTone _statusTone(String status) {
  switch (status) {
    case 'ok':
      return const _StatusTone(AppColors.success, AppColors.successLight);
    case 'error':
      return const _StatusTone(AppColors.error, AppColors.errorLight);
    case 'warning':
      return const _StatusTone(AppColors.warning, AppColors.warningLight);
    default:
      return const _StatusTone(AppColors.textPrimary, AppColors.surfaceVariant);
  }
}

class _StatusTone {
  const _StatusTone(this.foreground, this.background);

  final Color foreground;
  final Color background;
}

String _rolloutHeadline(String mode) {
  switch (mode) {
    case 'native_candidate':
      return 'Native Canary';
    case 'native_enforced':
      return 'Native Forced';
    case 'vectorized_python':
      return 'Vectorized';
    default:
      return 'Python Stable';
  }
}
