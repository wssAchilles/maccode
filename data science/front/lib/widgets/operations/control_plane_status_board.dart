/// Rust control-plane telemetry board.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ControlPlaneStatusBoard extends StatelessWidget {
  const ControlPlaneStatusBoard({
    super.key,
    required this.status,
  });

  final ControlPlaneStatus status;

  @override
  Widget build(BuildContext context) {
    final tone = _statusTone(status.status);
    return DutySectionBlock(
      title: '控制面',
      subtitle: '展示 Rust orchestrator 的实时接入状态、并发车道和派发预算。',
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
                  label: status.enabled ? 'ORCH ENABLED' : 'ORCH DISABLED',
                  foreground: tone.foreground,
                  background: tone.background,
                ),
                _Pill(
                  label: 'MODE · ${status.executionMode.isEmpty ? '--' : status.executionMode}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label: 'ACTIVE · ${status.activeOperations}',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
                _Pill(
                  label: 'TIMEOUT · ${status.dispatchTimeoutS}s',
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              status.message.isEmpty ? '控制面状态正常' : status.message,
              style: AppTextStyles.bodySmall.copyWith(
                color: tone.foreground,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _LaneCard(
                    label: 'Light Lane',
                    lane: status.lightLane,
                    accent: AppColors.info,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _LaneCard(
                    label: 'Heavy Lane',
                    lane: status.heavyLane,
                    accent: AppColors.warning,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              status.pythonWorkerConfigured
                  ? 'Python worker 已接入 orchestrator'
                  : 'Python worker 尚未完整接入 orchestrator',
              style: AppTextStyles.bodySmall.copyWith(
                color: status.pythonWorkerConfigured
                    ? AppColors.textSecondary
                    : AppColors.warning,
              ),
            ),
            if (status.orchestratorUrl.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                status.orchestratorUrl,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LaneCard extends StatelessWidget {
  const _LaneCard({
    required this.label,
    required this.lane,
    required this.accent,
  });

  final String label;
  final ControlPlaneLane lane;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.labelMedium),
          const SizedBox(height: 8),
          Text(
            '${lane.inUse}/${lane.capacity}',
            style: AppTextStyles.h4,
          ),
          const SizedBox(height: 6),
          Text(
            '占用 / 容量',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: lane.capacity == 0 ? 0 : lane.inUse / lane.capacity,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            color: accent,
            backgroundColor: AppColors.surfaceVariant,
          ),
          const SizedBox(height: 8),
          Text(
            '可用 ${lane.available}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
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
