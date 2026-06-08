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

class WorkspaceDigestListItem {
  const WorkspaceDigestListItem({
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
}

class WorkspaceDigestList extends StatelessWidget {
  const WorkspaceDigestList({super.key, required this.items});

  final List<WorkspaceDigestListItem> items;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        children: [
          for (var index = 0; index < items.length; index++) ...[
            _WorkspaceDigestListRow(item: items[index]),
            if (index < items.length - 1)
              const Divider(height: 1, color: AppColors.border),
          ],
        ],
      ),
    );
  }
}

class _WorkspaceDigestListRow extends StatelessWidget {
  const _WorkspaceDigestListRow({required this.item});

  final WorkspaceDigestListItem item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: item.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Icon(item.icon, size: 17, color: item.accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(item.title, style: AppTextStyles.labelLarge),
                    ),
                    if (item.highlighted &&
                        (item.highlightLabel ?? '').isNotEmpty)
                      Text(
                        item.highlightLabel!,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: item.accent,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  item.value,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (item.onCopy != null) ...[
            const SizedBox(width: 8),
            IconButton(
              onPressed: item.onCopy,
              tooltip: '复制${item.title}',
              icon: const Icon(Icons.content_copy_rounded, size: 18),
              visualDensity: VisualDensity.compact,
            ),
          ],
        ],
      ),
    );
  }
}
