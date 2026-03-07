/// 能源优化仪表盘页面
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/modeling_controls_state.dart';
import '../models/optimization_result.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/modeling_view_model.dart';
import '../widgets/modeling/modeling_control_panel.dart';
import '../widgets/modeling/modeling_results_section.dart';
import '../widgets/responsive_wrapper.dart';

class ModelingScreen extends StatefulWidget {
  const ModelingScreen({
    super.key,
    this.viewModel,
    this.nowBuilder,
  });

  final ModelingViewModel? viewModel;
  final DateTime Function()? nowBuilder;

  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}

class _ModelingScreenState extends State<ModelingScreen> {
  late final ModelingViewModel _viewModel;
  late final bool _ownsViewModel;
  late ModelingControlsState _controls;

  bool get _isLoading => _viewModel.isLoading;
  OptimizationResponse? get _result => _viewModel.result;
  OptimizationResponse? get _previousResult => _viewModel.previousResult;
  String? get _errorMessage => _viewModel.errorMessage;

  @override
  void initState() {
    super.initState();
    _viewModel = widget.viewModel ?? ModelingViewModel();
    _ownsViewModel = widget.viewModel == null;
    _controls = ModelingControlsState.initial(now: _now);
  }

  DateTime get _now => (widget.nowBuilder ?? DateTime.now).call();

  @override
  void dispose() {
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  Future<void> _runOptimization({bool saveForComparison = true}) async {
    final result = await _viewModel.runOptimization(
      initialSoc: _controls.initialSoc,
      targetDate: _controls.targetDate,
      batteryCapacity: _controls.batteryCapacity,
      batteryPower: _controls.maxPower,
      temperatureAdjust: _controls.temperatureAdjust,
      saveForComparison: saveForComparison,
    );

    if (!mounted) {
      return;
    }

    if (result == null) {
      final message = _errorMessage;
      if (message != null) {
        _showErrorSnackBar(message);
      }
      return;
    }

    if (result.isSuccess) {
      _showSuccessSnackBar(
        '优化完成！节省 ${result.optimization?.summary.savingsFormatted ?? "0"}',
      );
      return;
    }

    final message = _errorMessage;
    if (message != null) {
      _showErrorSnackBar(message);
    }
  }

  Future<void> _refreshResults() async {
    if (_isLoading || _result == null) {
      return;
    }

    await _runOptimization(saveForComparison: false);
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  void _updateControls(ModelingControlsState nextState) {
    setState(() {
      _controls = nextState;
    });
  }

  Future<void> _selectDate() async {
    final now = _now;
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _controls.targetDate,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: DateTime(now.year, now.month, now.day).add(
        const Duration(days: 7),
      ),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue[700]!,
              onPrimary: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );

    if (!mounted || picked == null || picked == _controls.targetDate) {
      return;
    }

    _updateControls(_controls.copyWith(targetDate: picked));
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _viewModel,
      builder: (context, _) {
        return Scaffold(
          backgroundColor: AppColors.background,
          body: RefreshIndicator(
            onRefresh: _refreshResults,
            child: ResponsiveWrapper(
              maxWidth: ResponsiveHelper.getMaxContentWidth(context),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: ResponsiveHelper.getPagePadding(context),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ModelingControlPanel(
                      state: _controls,
                      isLoading: _isLoading,
                      onToggleAdvancedParams: () {
                        _updateControls(
                          _controls.copyWith(
                            showAdvancedParams: !_controls.showAdvancedParams,
                          ),
                        );
                      },
                      onScenarioChanged: (scenario) {
                        _updateControls(_controls.applyScenario(scenario));
                      },
                      onInitialSocChanged: (value) {
                        _updateControls(_controls.copyWith(initialSoc: value));
                      },
                      onBatteryCapacityChanged: (value) {
                        _updateControls(
                          _controls.copyWith(batteryCapacity: value),
                        );
                      },
                      onMaxPowerChanged: (value) {
                        _updateControls(_controls.copyWith(maxPower: value));
                      },
                      onTemperatureAdjustChanged: (value) {
                        _updateControls(
                          _controls.copyWith(temperatureAdjust: value),
                        );
                      },
                      onSelectDate: _selectDate,
                      onRunOptimization: _runOptimization,
                    ),
                    const SizedBox(height: 16),
                    ModelingResultsSection(
                      isLoading: _isLoading,
                      errorMessage: _errorMessage,
                      result: _result,
                      previousResult: _previousResult,
                      onDismissError: _viewModel.clearError,
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
