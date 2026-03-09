/// 快捷动作区
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class QuickActionsSection extends StatelessWidget {
  const QuickActionsSection({super.key, required this.actions});

  final List<QuickActionItem> actions;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('快捷动作', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: actions
                .map(
                  (item) => SizedBox(
                    width: 220,
                    child: FilledButton.tonalIcon(
                      onPressed: item.onTap,
                      icon: Icon(item.icon),
                      label: Text(item.label),
                      style: FilledButton.styleFrom(
                        foregroundColor: item.emphasis
                            ? Colors.white
                            : AppColors.textPrimary,
                        backgroundColor: item.emphasis
                            ? AppColors.cta
                            : AppColors.surfaceVariant,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(
                            AppDecorations.radiusMd,
                          ),
                        ),
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class QuickActionItem {
  const QuickActionItem({
    required this.label,
    required this.icon,
    required this.onTap,
    this.emphasis = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool emphasis;
}
