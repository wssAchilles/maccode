/// 驾驶舱系统状态条
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../utils/system_status_localizer.dart';

class SystemStatusStrip extends StatelessWidget {
  const SystemStatusStrip({
    super.key,
    required this.items,
    this.compact = false,
    this.trailing,
  });

  final List<SystemStatusItem> items;
  final bool compact;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    final statusWrap = Wrap(
      spacing: 12,
      runSpacing: 8,
      children: items.map(_buildItem).toList(growable: false),
    );

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 12 : 20,
        vertical: compact ? 10 : 12,
      ),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: const Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: trailing == null
          ? statusWrap
          : Row(
              children: [
                Expanded(child: statusWrap),
                const SizedBox(width: 12),
                trailing!,
              ],
            ),
    );
  }

  Widget _buildItem(SystemStatusItem item) {
    final tone = _StatusTone.fromStatus(item.status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: tone.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        border: Border.all(color: tone.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(tone.icon, size: 14, color: tone.foreground),
          const SizedBox(width: 8),
          Text(
            localizeSystemStatusLabel(item.label),
            style: AppTextStyles.labelMedium.copyWith(
              color: tone.foreground,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            localizeSystemStatusMessage(item.message),
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _StatusTone {
  const _StatusTone({
    required this.foreground,
    required this.background,
    required this.border,
    required this.icon,
  });

  final Color foreground;
  final Color background;
  final Color border;
  final IconData icon;

  factory _StatusTone.fromStatus(String status) {
    switch (status) {
      case 'ok':
        return const _StatusTone(
          foreground: AppColors.success,
          background: AppColors.successLight,
          border: Color(0x6622C55E),
          icon: Icons.check_circle_rounded,
        );
      case 'warning':
        return const _StatusTone(
          foreground: AppColors.warning,
          background: AppColors.warningLight,
          border: Color(0x66EAB308),
          icon: Icons.warning_amber_rounded,
        );
      case 'error':
        return const _StatusTone(
          foreground: AppColors.error,
          background: AppColors.errorLight,
          border: Color(0x66EF4444),
          icon: Icons.error_rounded,
        );
      default:
        return const _StatusTone(
          foreground: AppColors.textSecondary,
          background: AppColors.surfaceVariant,
          border: AppColors.border,
          icon: Icons.radio_button_checked,
        );
    }
  }
}
