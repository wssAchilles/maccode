/// 统一 incident 卡片头
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import 'workspace_action_lane.dart';

class IncidentCardHeader extends StatelessWidget {
  const IncidentCardHeader({
    super.key,
    required this.accent,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.supportingText,
    this.supportingColor,
    this.trailing,
    this.workspaceLabel,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
  });

  final Color accent;
  final IconData icon;
  final String title;
  final String subtitle;
  final String? supportingText;
  final Color? supportingColor;
  final Widget? trailing;
  final String? workspaceLabel;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Icon(icon, color: accent, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: AppTextStyles.h4),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  if ((supportingText ?? '').isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      supportingText!,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: supportingColor ?? accent,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            ...?(trailing == null ? null : <Widget>[trailing!]),
          ],
        ),
        if ((workspaceLabel ?? '').isNotEmpty ||
            (cardLabel ?? '').isNotEmpty ||
            (incidentLabel ?? '').isNotEmpty ||
            (summary ?? '').isNotEmpty) ...[
          const SizedBox(height: 12),
          WorkspaceContextBanner(
            accent: accent,
            workspaceLabel: workspaceLabel,
            cardLabel: cardLabel,
            incidentLabel: incidentLabel,
            summary: summary,
          ),
        ],
      ],
    );
  }
}
