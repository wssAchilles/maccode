/// 共享工作台动作车道
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../utils/asset_chain_context.dart';

class WorkspaceActionLane extends StatelessWidget {
  const WorkspaceActionLane({
    super.key,
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    required this.statusLabel,
    required this.statusColor,
    required this.actions,
    this.recommendedActionKey,
    this.workspaceLabel,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
    this.contextMode = WorkspaceContextMode.compact,
  });

  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String statusLabel;
  final Color statusColor;
  final List<WorkspaceActionLaneAction> actions;
  final String? recommendedActionKey;
  final String? workspaceLabel;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;
  final WorkspaceContextMode contextMode;

  @override
  Widget build(BuildContext context) {
    final effectiveCardLabel = buildDutyContextCardValue(cardLabel);
    final effectiveIncidentLabel = buildDutyContextIncidentValue(incidentLabel);
    final effectiveSummary = sanitizeWorkspaceSummaryText(
      summary,
      duplicatedLabels: [
        workspaceLabel,
        effectiveCardLabel,
        effectiveIncidentLabel,
      ],
    );
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, size: 18, color: accent),
              ),
              const SizedBox(width: 10),
              Expanded(child: Text(title, style: AppTextStyles.labelLarge)),
              if ((workspaceLabel ?? '').isNotEmpty) ...[
                WorkspaceStatusChip(
                  label: workspaceLabel!,
                  icon: Icons.account_tree_rounded,
                  foreground: accent,
                  background: accent.withValues(alpha: 0.12),
                ),
                const SizedBox(width: 8),
              ],
              WorkspaceStatusChip(
                label: statusLabel,
                icon: Icons.radio_button_checked_rounded,
                foreground: statusColor,
                background: statusColor.withValues(alpha: 0.12),
              ),
            ],
          ),
          if ((workspaceLabel ?? '').isNotEmpty ||
              (effectiveCardLabel ?? '').isNotEmpty ||
              (effectiveIncidentLabel ?? '').isNotEmpty ||
              (effectiveSummary ?? '').isNotEmpty) ...[
            const SizedBox(height: 12),
            WorkspaceContextBanner(
              accent: accent,
              mode: contextMode,
              workspaceLabel: workspaceLabel,
              cardLabel: effectiveCardLabel,
              incidentLabel: effectiveIncidentLabel,
              summary: effectiveSummary,
            ),
          ],
          const SizedBox(height: 10),
          Text(
            description,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _prioritizedActions(actions, recommendedActionKey)
                .map(
                  (action) => action.build(
                    context,
                    recommended: action.semanticKey == recommendedActionKey,
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class WorkspaceInlineActionBar extends StatelessWidget {
  const WorkspaceInlineActionBar({
    super.key,
    required this.actions,
    this.recommendedActionKey,
    this.spacing = 8,
    this.runSpacing = 8,
    this.visibleActionCount = 2,
  });

  final List<WorkspaceActionLaneAction> actions;
  final String? recommendedActionKey;
  final double spacing;
  final double runSpacing;
  final int visibleActionCount;

  @override
  Widget build(BuildContext context) {
    final prioritized = _prioritizedActions(actions, recommendedActionKey);
    final visibleCount = visibleActionCount.clamp(1, prioritized.length);
    final visibleActions = prioritized
        .take(visibleCount)
        .toList(growable: false);
    final overflowActions = prioritized
        .skip(visibleCount)
        .toList(growable: false);

    return Wrap(
      spacing: spacing,
      runSpacing: runSpacing,
      children: [
        ...visibleActions.map(
          (action) => action.build(
            context,
            recommended: action.semanticKey == recommendedActionKey,
          ),
        ),
        if (overflowActions.isNotEmpty)
          _WorkspaceActionOverflowMenu(actions: overflowActions),
      ],
    );
  }
}

class WorkspaceActionDeck extends StatelessWidget {
  const WorkspaceActionDeck({
    super.key,
    required this.lanes,
    this.breakpoint = 980,
    this.spacing = 12,
  });

  final List<Widget> lanes;
  final double breakpoint;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < breakpoint;
        if (stacked) {
          return Column(
            children: [
              for (var i = 0; i < lanes.length; i++) ...[
                lanes[i],
                if (i < lanes.length - 1) SizedBox(height: spacing),
              ],
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < lanes.length; i++) ...[
              Expanded(child: lanes[i]),
              if (i < lanes.length - 1) SizedBox(width: spacing),
            ],
          ],
        );
      },
    );
  }
}

class WorkspaceActionLaneAction {
  const WorkspaceActionLaneAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.semanticKey,
    this.tone = WorkspaceActionLaneTone.outline,
    this.isLoading = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final String? semanticKey;
  final WorkspaceActionLaneTone tone;
  final bool isLoading;

  Widget build(BuildContext context, {bool recommended = false}) {
    final iconWidget = isLoading
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Icon(icon);
    final effectiveTone = _elevatedTone(tone, recommended: recommended);
    switch (effectiveTone) {
      case WorkspaceActionLaneTone.primary:
        return FilledButton.icon(
          onPressed: onTap,
          icon: iconWidget,
          label: Text(label),
        );
      case WorkspaceActionLaneTone.tonal:
        return FilledButton.tonalIcon(
          onPressed: onTap,
          icon: iconWidget,
          label: Text(label),
        );
      case WorkspaceActionLaneTone.outline:
        return OutlinedButton.icon(
          onPressed: onTap,
          icon: iconWidget,
          label: Text(label),
        );
    }
  }
}

enum WorkspaceActionLaneTone { primary, tonal, outline }

enum WorkspaceContextMode { none, compact, full }

List<WorkspaceActionLaneAction> _prioritizedActions(
  List<WorkspaceActionLaneAction> actions,
  String? recommendedActionKey,
) {
  if (recommendedActionKey == null || recommendedActionKey.isEmpty) {
    return actions;
  }
  final prioritized = [...actions];
  prioritized.sort((a, b) {
    final aPriority = a.semanticKey == recommendedActionKey ? 1 : 0;
    final bPriority = b.semanticKey == recommendedActionKey ? 1 : 0;
    return bPriority.compareTo(aPriority);
  });
  return prioritized;
}

WorkspaceActionLaneTone _elevatedTone(
  WorkspaceActionLaneTone tone, {
  required bool recommended,
}) {
  if (!recommended) {
    return tone;
  }
  switch (tone) {
    case WorkspaceActionLaneTone.primary:
      return WorkspaceActionLaneTone.primary;
    case WorkspaceActionLaneTone.tonal:
      return WorkspaceActionLaneTone.primary;
    case WorkspaceActionLaneTone.outline:
      return WorkspaceActionLaneTone.tonal;
  }
}

class WorkspaceContextBanner extends StatelessWidget {
  const WorkspaceContextBanner({
    super.key,
    required this.accent,
    this.mode = WorkspaceContextMode.compact,
    this.workspaceLabel,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
  });

  final Color accent;
  final WorkspaceContextMode mode;
  final String? workspaceLabel;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;

  @override
  Widget build(BuildContext context) {
    if (mode == WorkspaceContextMode.none) {
      return const SizedBox.shrink();
    }
    final effectiveCardLabel = buildDutyContextCardValue(cardLabel);
    final effectiveIncidentLabel = buildDutyContextIncidentValue(incidentLabel);
    final effectiveSummary = sanitizeWorkspaceSummaryText(
      summary,
      duplicatedLabels: [
        workspaceLabel,
        effectiveCardLabel,
        effectiveIncidentLabel,
      ],
    );
    final hasSignal =
        (workspaceLabel ?? '').isNotEmpty ||
        (effectiveCardLabel ?? '').isNotEmpty ||
        (effectiveIncidentLabel ?? '').isNotEmpty ||
        (effectiveSummary ?? '').isNotEmpty;
    if (!hasSignal) {
      return const SizedBox.shrink();
    }
    final chips = <Widget>[
      if ((workspaceLabel ?? '').isNotEmpty)
        WorkspaceStatusChip(
          label: workspaceLabel!,
          icon: Icons.account_tree_rounded,
          foreground: accent,
          background: accent.withValues(alpha: 0.12),
        ),
      if ((effectiveCardLabel ?? '').isNotEmpty)
        WorkspaceStatusChip(
          label: effectiveCardLabel!,
          icon: Icons.dashboard_customize_rounded,
          foreground: AppColors.textPrimary,
          background: AppColors.surfaceVariant,
        ),
      if ((effectiveIncidentLabel ?? '').isNotEmpty)
        WorkspaceStatusChip(
          label: mode == WorkspaceContextMode.full
              ? '当前关注 · $effectiveIncidentLabel'
              : effectiveIncidentLabel!,
          icon: Icons.priority_high_rounded,
          foreground: accent,
          background: accent.withValues(alpha: 0.12),
        ),
    ];
    final visibleChips = mode == WorkspaceContextMode.compact
        ? chips.take(2).toList(growable: false)
        : chips;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(spacing: 8, runSpacing: 8, children: visibleChips),
          if ((effectiveSummary ?? '').isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              effectiveSummary!,
              maxLines: mode == WorkspaceContextMode.compact ? 1 : null,
              overflow: mode == WorkspaceContextMode.compact
                  ? TextOverflow.ellipsis
                  : TextOverflow.visible,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WorkspaceActionOverflowMenu extends StatelessWidget {
  const _WorkspaceActionOverflowMenu({required this.actions});

  final List<WorkspaceActionLaneAction> actions;

  @override
  Widget build(BuildContext context) {
    return MenuAnchor(
      menuChildren: actions
          .map(
            (action) => MenuItemButton(
              leadingIcon: action.isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(action.icon),
              onPressed: action.onTap,
              child: Text(action.label),
            ),
          )
          .toList(growable: false),
      builder: (context, controller, child) {
        return OutlinedButton.icon(
          onPressed: () {
            controller.isOpen ? controller.close() : controller.open();
          },
          icon: const Icon(Icons.more_horiz_rounded),
          label: const Text('更多'),
        );
      },
    );
  }
}

class WorkspaceStatusChip extends StatelessWidget {
  const WorkspaceStatusChip({
    super.key,
    required this.label,
    required this.icon,
    required this.foreground,
    required this.background,
  });

  final String label;
  final IconData icon;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: foreground),
          const SizedBox(width: 8),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 220),
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.labelMedium.copyWith(
                color: foreground,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
