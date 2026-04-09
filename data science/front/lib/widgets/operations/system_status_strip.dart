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
    this.headline,
    this.maxVisibleItems,
  });

  final List<SystemStatusItem> items;
  final bool compact;
  final Widget? trailing;
  final String? headline;
  final int? maxVisibleItems;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    final visibleItems = _prioritizeItems(items);
    final limitedItems = maxVisibleItems == null
        ? visibleItems
        : visibleItems.take(maxVisibleItems!).toList(growable: false);

    final statusWrap = Wrap(
      spacing: 12,
      runSpacing: 8,
      children: limitedItems.map(_buildItem).toList(growable: false),
    );

    final content = Wrap(
      spacing: 12,
      runSpacing: 10,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if ((headline ?? '').isNotEmpty) _buildHeadlineChip(headline!),
        statusWrap,
      ],
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
          ? content
          : Row(
              children: [
                Expanded(child: content),
                const SizedBox(width: 12),
                trailing!,
              ],
            ),
    );
  }

  List<SystemStatusItem> _prioritizeItems(List<SystemStatusItem> items) {
    final sorted = [...items];
    sorted.sort((a, b) {
      final severityCompare = _severityWeight(
        a.status,
      ).compareTo(_severityWeight(b.status));
      if (severityCompare != 0) {
        return severityCompare;
      }
      return a.label.compareTo(b.label);
    });
    return sorted;
  }

  int _severityWeight(String status) {
    switch (status) {
      case 'error':
        return 0;
      case 'warning':
        return 1;
      case 'ok':
      case 'healthy':
        return 2;
      default:
        return 3;
    }
  }

  Widget _buildHeadlineChip(String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.infoLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.12)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.visibility_rounded,
            size: 14,
            color: AppColors.primary,
          ),
          const SizedBox(width: 8),
          Text(
            value,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
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
