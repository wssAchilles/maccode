part of '../modeling_control_panel.dart';

class _SliderConfig {
  const _SliderConfig({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.displayValue,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final double value;
  final double min;
  final double max;
  final int divisions;
  final String displayValue;
}

class _SliderField extends StatelessWidget {
  const _SliderField({
    required this.config,
    required this.isLoading,
    required this.isCompact,
    required this.onChanged,
  });

  final _SliderConfig config;
  final bool isLoading;
  final bool isCompact;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(config.icon, color: config.iconColor, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(config.label, style: AppTextStyles.labelMedium),
              ),
              _SliderValueBadge(
                value: config.displayValue,
                color: config.iconColor,
              ),
            ],
          ),
          SliderTheme(
            data: const SliderThemeData(
              trackHeight: 4,
              thumbShape: RoundSliderThumbShape(enabledThumbRadius: 8),
            ),
            child: Slider(
              value: config.value,
              min: config.min,
              max: config.max,
              divisions: config.divisions,
              activeColor: config.iconColor,
              inactiveColor: config.iconColor.withValues(alpha: 0.2),
              onChanged: isLoading ? null : onChanged,
            ),
          ),
        ],
      );
    }

    return Row(
      children: [
        Icon(config.icon, color: config.iconColor, size: 20),
        const SizedBox(width: 8),
        SizedBox(
          width: 116,
          child: Text(config.label, style: AppTextStyles.labelMedium),
        ),
        Expanded(
          child: SliderTheme(
            data: const SliderThemeData(
              trackHeight: 4,
              thumbShape: RoundSliderThumbShape(enabledThumbRadius: 8),
            ),
            child: Slider(
              value: config.value,
              min: config.min,
              max: config.max,
              divisions: config.divisions,
              activeColor: config.iconColor,
              inactiveColor: config.iconColor.withValues(alpha: 0.2),
              onChanged: isLoading ? null : onChanged,
            ),
          ),
        ),
        _SliderValueBadge(value: config.displayValue, color: config.iconColor),
      ],
    );
  }
}

class _SliderValueBadge extends StatelessWidget {
  const _SliderValueBadge({required this.value, required this.color});

  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 78,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusSm),
      ),
      child: Text(
        value,
        textAlign: TextAlign.center,
        style: AppTextStyles.labelMedium.copyWith(
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }
}
