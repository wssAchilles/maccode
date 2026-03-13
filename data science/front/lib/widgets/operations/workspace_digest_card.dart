/// 共享工作台摘要卡
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class WorkspaceDigestCard extends StatelessWidget {
  const WorkspaceDigestCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    required this.accent,
    this.onCopy,
    this.highlighted = false,
    this.highlightLabel,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color accent;
  final VoidCallback? onCopy;
  final bool highlighted;
  final String? highlightLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: highlighted
            ? Border.all(color: accent.withValues(alpha: 0.28))
            : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: accent),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: AppTextStyles.labelLarge)),
              if (onCopy != null)
                IconButton(
                  onPressed: onCopy,
                  tooltip: '复制$title',
                  icon: const Icon(Icons.content_copy_rounded, size: 18),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          if (highlighted && (highlightLabel ?? '').isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              highlightLabel!,
              style: AppTextStyles.labelMedium.copyWith(color: accent),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
