/// 建模页面输入参数状态
library;

import '../config/constants.dart';

enum ModelingScenario { summer, winter, overtime }

class ModelingControlsState {
  const ModelingControlsState({
    required this.initialSoc,
    required this.targetDate,
    required this.batteryCapacity,
    required this.maxPower,
    required this.showAdvancedParams,
    required this.selectedScenario,
    required this.temperatureAdjust,
  });

  factory ModelingControlsState.initial({DateTime? now}) {
    final baseNow = now ?? DateTime.now();
    final normalizedNow = DateTime(baseNow.year, baseNow.month, baseNow.day);

    return ModelingControlsState(
      initialSoc: AppConstants.defaultInitialSoc,
      targetDate: normalizedNow.add(const Duration(days: 1)),
      batteryCapacity: 500,
      maxPower: 200,
      showAdvancedParams: false,
      selectedScenario: null,
      temperatureAdjust: 0,
    );
  }

  final double initialSoc;
  final DateTime targetDate;
  final double batteryCapacity;
  final double maxPower;
  final bool showAdvancedParams;
  final ModelingScenario? selectedScenario;
  final double temperatureAdjust;

  ModelingControlsState copyWith({
    double? initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? maxPower,
    bool? showAdvancedParams,
    ModelingScenario? selectedScenario,
    bool clearScenario = false,
    double? temperatureAdjust,
  }) {
    return ModelingControlsState(
      initialSoc: initialSoc ?? this.initialSoc,
      targetDate: targetDate ?? this.targetDate,
      batteryCapacity: batteryCapacity ?? this.batteryCapacity,
      maxPower: maxPower ?? this.maxPower,
      showAdvancedParams: showAdvancedParams ?? this.showAdvancedParams,
      selectedScenario: clearScenario
          ? null
          : (selectedScenario ?? this.selectedScenario),
      temperatureAdjust: temperatureAdjust ?? this.temperatureAdjust,
    );
  }

  ModelingControlsState applyScenario(ModelingScenario? scenario) {
    if (scenario == null) {
      return copyWith(clearScenario: true, temperatureAdjust: 0);
    }

    return copyWith(
      selectedScenario: scenario,
      showAdvancedParams: true,
      temperatureAdjust: switch (scenario) {
        ModelingScenario.summer => 5,
        ModelingScenario.winter => -5,
        ModelingScenario.overtime => 0,
      },
    );
  }

  String get summaryText {
    final buffer = StringBuffer(
      '${batteryCapacity.toInt()}kWh | ${maxPower.toInt()}kW | '
      '${(initialSoc * 100).toInt()}%',
    );

    if (temperatureAdjust != 0) {
      buffer.write(
        ' | ${temperatureAdjust >= 0 ? "+" : ""}${temperatureAdjust.toInt()}°C',
      );
    }

    return buffer.toString();
  }
}
