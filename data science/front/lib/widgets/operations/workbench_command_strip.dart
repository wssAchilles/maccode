/// Shared page-level command strip for embedded workbenches.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class WorkbenchCommandStrip extends StatelessWidget {
  const WorkbenchCommandStrip({
    super.key,
    required this.title,
    required this.description,
    required this.actions,
  });

  final String title;
  final String description;
  final List<WorkbenchCommandAction> actions;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTextStyles.h4),
          const SizedBox(height: 6),
          Text(
            description,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: actions
                .map(
                  (action) => SizedBox(
                    width: 220,
                    child: _WorkbenchCommandButton(action: action),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class WorkbenchCommandAction {
  const WorkbenchCommandAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.tone = WorkbenchCommandTone.tonal,
    this.isLoading = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final WorkbenchCommandTone tone;
  final bool isLoading;
}

enum WorkbenchCommandTone { primary, tonal, outline }

class _WorkbenchCommandButton extends StatelessWidget {
  const _WorkbenchCommandButton({required this.action});

  final WorkbenchCommandAction action;

  @override
  Widget build(BuildContext context) {
    final icon = action.isLoading
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Icon(action.icon);

    final label = Text(action.label);

    switch (action.tone) {
      case WorkbenchCommandTone.primary:
        return FilledButton.icon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.cta,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
      case WorkbenchCommandTone.tonal:
        return FilledButton.tonalIcon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
      case WorkbenchCommandTone.outline:
        return OutlinedButton.icon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
    }
  }
}
