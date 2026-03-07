part of '../modeling_control_panel.dart';

class _ModelingPanelHeader extends StatelessWidget {
  const _ModelingPanelHeader({
    required this.showAdvancedParams,
    required this.isCompact,
    required this.onToggleAdvancedParams,
  });

  final bool showAdvancedParams;
  final bool isCompact;
  final VoidCallback onToggleAdvancedParams;

  @override
  Widget build(BuildContext context) {
    final title = Expanded(child: Text('优化沙盒', style: AppTextStyles.h3));
    final toggle = TextButton.icon(
      key: const ValueKey('modeling-toggle-advanced'),
      onPressed: onToggleAdvancedParams,
      icon: Icon(
        showAdvancedParams ? Icons.expand_less : Icons.expand_more,
        size: 20,
        color: AppColors.textMuted,
      ),
      label: Text(
        showAdvancedParams ? '收起' : '高级',
        style: AppTextStyles.labelMedium,
      ),
    );

    if (isCompact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [_buildHeaderIcon(), const SizedBox(width: 12), title]),
          const SizedBox(height: 8),
          toggle,
        ],
      );
    }

    return Row(
      children: [_buildHeaderIcon(), const SizedBox(width: 12), title, toggle],
    );
  }

  Widget _buildHeaderIcon() {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: const Icon(Icons.tune_rounded, color: AppColors.primary, size: 20),
    );
  }
}

class _ScenarioSection extends StatelessWidget {
  const _ScenarioSection({
    required this.selectedScenario,
    required this.isLoading,
    required this.onScenarioChanged,
  });

  final ModelingScenario? selectedScenario;
  final bool isLoading;
  final ValueChanged<ModelingScenario?> onScenarioChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '快速场景',
          style: AppTextStyles.labelMedium.copyWith(color: AppColors.textMuted),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _ScenarioChip(
              scenario: ModelingScenario.summer,
              label: '夏季高温',
              color: AppColors.warning,
              icon: Icons.wb_sunny_rounded,
              selectedScenario: selectedScenario,
              isLoading: isLoading,
              onScenarioChanged: onScenarioChanged,
            ),
            _ScenarioChip(
              scenario: ModelingScenario.winter,
              label: '冬季寒潮',
              color: AppColors.info,
              icon: Icons.ac_unit_rounded,
              selectedScenario: selectedScenario,
              isLoading: isLoading,
              onScenarioChanged: onScenarioChanged,
            ),
            _ScenarioChip(
              scenario: ModelingScenario.overtime,
              label: '夜间加班',
              color: const Color(0xFF8B5CF6),
              icon: Icons.nightlight_round,
              selectedScenario: selectedScenario,
              isLoading: isLoading,
              onScenarioChanged: onScenarioChanged,
            ),
          ],
        ),
      ],
    );
  }
}

class _ScenarioChip extends StatelessWidget {
  const _ScenarioChip({
    required this.scenario,
    required this.label,
    required this.color,
    required this.icon,
    required this.selectedScenario,
    required this.isLoading,
    required this.onScenarioChanged,
  });

  final ModelingScenario scenario;
  final String label;
  final Color color;
  final IconData icon;
  final ModelingScenario? selectedScenario;
  final bool isLoading;
  final ValueChanged<ModelingScenario?> onScenarioChanged;

  @override
  Widget build(BuildContext context) {
    final isSelected = selectedScenario == scenario;

    return FilterChip(
      key: ValueKey('modeling-scenario-${scenario.name}'),
      avatar: Icon(icon, size: 16, color: isSelected ? Colors.white : color),
      label: Text(
        label,
        style: AppTextStyles.labelSmall.copyWith(
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
          color: isSelected ? Colors.white : AppColors.textPrimary,
        ),
      ),
      selected: isSelected,
      onSelected: isLoading
          ? null
          : (selected) => onScenarioChanged(selected ? scenario : null),
      backgroundColor: color.withValues(alpha: 0.1),
      selectedColor: color,
      checkmarkColor: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        side: BorderSide(
          color: isSelected ? color : color.withValues(alpha: 0.3),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }
}

class _TargetDateSection extends StatelessWidget {
  const _TargetDateSection({
    required this.targetDate,
    required this.isLoading,
    required this.isCompact,
    required this.onSelectDate,
  });

  final DateTime targetDate;
  final bool isLoading;
  final bool isCompact;
  final VoidCallback onSelectDate;

  @override
  Widget build(BuildContext context) {
    final labelRow = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.calendar_today, color: Colors.orange, size: 20),
        const SizedBox(width: 8),
        Text('目标日期', style: AppTextStyles.labelLarge),
      ],
    );

    final selector = InkWell(
      key: const ValueKey('modeling-select-date'),
      onTap: isLoading ? null : onSelectDate,
      borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              DateFormat('MM-dd').format(targetDate),
              style: AppTextStyles.bodyMedium,
            ),
            const SizedBox(width: 4),
            Icon(Icons.arrow_drop_down, color: AppColors.textMuted, size: 20),
          ],
        ),
      ),
    );

    if (isCompact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [labelRow, const SizedBox(height: 12), selector],
      );
    }

    return Row(children: [labelRow, const Spacer(), selector]);
  }
}

class _SummaryBanner extends StatelessWidget {
  const _SummaryBanner({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const ValueKey('modeling-summary-banner'),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline, color: AppColors.textMuted, size: 16),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: AppTextStyles.bodySmall)),
        ],
      ),
    );
  }
}
