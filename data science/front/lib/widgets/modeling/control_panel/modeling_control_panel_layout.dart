part of '../modeling_control_panel.dart';

class ModelingControlPanel extends StatelessWidget {
  const ModelingControlPanel({
    super.key,
    required this.state,
    required this.isLoading,
    required this.onToggleAdvancedParams,
    required this.onScenarioChanged,
    required this.onInitialSocChanged,
    required this.onBatteryCapacityChanged,
    required this.onMaxPowerChanged,
    required this.onTemperatureAdjustChanged,
    required this.onSelectDate,
    required this.onRunOptimization,
  });

  final ModelingControlsState state;
  final bool isLoading;
  final VoidCallback onToggleAdvancedParams;
  final ValueChanged<ModelingScenario?> onScenarioChanged;
  final ValueChanged<double> onInitialSocChanged;
  final ValueChanged<double> onBatteryCapacityChanged;
  final ValueChanged<double> onMaxPowerChanged;
  final ValueChanged<double> onTemperatureAdjustChanged;
  final VoidCallback onSelectDate;
  final VoidCallback onRunOptimization;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      enableHover: false,
      padding: const EdgeInsets.all(20),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 520;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _ModelingPanelHeader(
                showAdvancedParams: state.showAdvancedParams,
                isCompact: isCompact,
                onToggleAdvancedParams: onToggleAdvancedParams,
              ),
              const SizedBox(height: 20),
              _ScenarioSection(
                selectedScenario: state.selectedScenario,
                isLoading: isLoading,
                onScenarioChanged: onScenarioChanged,
              ),
              Divider(height: 32, color: AppColors.border),
              _SliderField(
                config: _SliderConfig(
                  icon: Icons.battery_charging_full,
                  iconColor: Colors.green,
                  label: '初始电量',
                  value: state.initialSoc,
                  min: 0,
                  max: 1,
                  divisions: 20,
                  displayValue: '${(state.initialSoc * 100).toInt()}%',
                ),
                isLoading: isLoading,
                isCompact: isCompact,
                onChanged: onInitialSocChanged,
              ),
              if (state.showAdvancedParams) ...[
                const SizedBox(height: 16),
                _SliderField(
                  config: _SliderConfig(
                    icon: Icons.battery_full,
                    iconColor: Colors.blue,
                    label: '电池容量 (商业微网)',
                    value: state.batteryCapacity,
                    min: 100,
                    max: 2000,
                    divisions: 19,
                    displayValue: '${state.batteryCapacity.toInt()} kWh',
                  ),
                  isLoading: isLoading,
                  isCompact: isCompact,
                  onChanged: onBatteryCapacityChanged,
                ),
                const SizedBox(height: 16),
                _SliderField(
                  config: _SliderConfig(
                    icon: Icons.flash_on,
                    iconColor: Colors.amber,
                    label: '最大功率 (微网级)',
                    value: state.maxPower,
                    min: 50,
                    max: 1000,
                    divisions: 19,
                    displayValue: '${state.maxPower.toInt()} kW',
                  ),
                  isLoading: isLoading,
                  isCompact: isCompact,
                  onChanged: onMaxPowerChanged,
                ),
                const SizedBox(height: 16),
                _SliderField(
                  config: _SliderConfig(
                    icon: Icons.thermostat,
                    iconColor: Colors.red,
                    label: '温度调整 (What-If)',
                    value: state.temperatureAdjust,
                    min: -5,
                    max: 5,
                    divisions: 10,
                    displayValue:
                        '${state.temperatureAdjust >= 0 ? "+" : ""}'
                        '${state.temperatureAdjust.toInt()}°C',
                  ),
                  isLoading: isLoading,
                  isCompact: isCompact,
                  onChanged: onTemperatureAdjustChanged,
                ),
              ],
              const SizedBox(height: 16),
              _TargetDateSection(
                targetDate: state.targetDate,
                isLoading: isLoading,
                isCompact: isCompact,
                onSelectDate: onSelectDate,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  key: const ValueKey('modeling-run-button'),
                  onPressed: isLoading ? null : onRunOptimization,
                  icon: isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.bolt_rounded, size: 22),
                  label: Text(
                    isLoading ? '优化中...' : '开始智能调度',
                    style: AppTextStyles.button,
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.cta,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(
                        AppDecorations.radiusMd,
                      ),
                    ),
                    elevation: 0,
                  ),
                ),
              ),
              if (state.showAdvancedParams ||
                  state.selectedScenario != null) ...[
                const SizedBox(height: 12),
                _SummaryBanner(text: state.summaryText),
              ],
            ],
          );
        },
      ),
    );
  }
}
