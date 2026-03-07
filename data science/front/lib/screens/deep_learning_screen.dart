/// 深度学习实验室页面
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/deep_learning_config_state.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/deep_learning_view_model.dart';
import '../widgets/deep_learning/deep_learning_config_panel.dart';
import '../widgets/deep_learning/deep_learning_header.dart';
import '../widgets/deep_learning/deep_learning_terminal_panel.dart';
import '../widgets/responsive_wrapper.dart';

class DeepLearningScreen extends StatefulWidget {
  const DeepLearningScreen({
    super.key,
    this.storagePath,
    this.viewModel,
  });

  final String? storagePath;
  final DeepLearningViewModel? viewModel;

  @override
  State<DeepLearningScreen> createState() => _DeepLearningScreenState();
}

class _DeepLearningScreenState extends State<DeepLearningScreen> {
  late final DeepLearningViewModel _viewModel;
  late final bool _ownsViewModel;
  DeepLearningConfigState _config = const DeepLearningConfigState.initial();

  bool get _isTraining => _viewModel.isTraining;
  String get _trainLogs => _viewModel.trainLogs;

  @override
  void initState() {
    super.initState();
    _viewModel = widget.viewModel ?? DeepLearningViewModel();
    _ownsViewModel = widget.viewModel == null;
  }

  @override
  void dispose() {
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  Future<void> _startTraining() async {
    final success = await _viewModel.startTraining(
      storagePath: widget.storagePath ?? 'demo_data.csv',
      modelType: _config.modelTypeValue,
      epochs: _config.epochs,
      batchSize: _config.batchSize,
      windowSize: _config.windowSize,
      targetColumn: 'Load',
    );

    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          success
              ? 'Cloud training completed successfully.'
              : 'Cloud training failed. Review the logs for details.',
        ),
        backgroundColor: success ? AppColors.success : AppColors.error,
      ),
    );
  }

  void _updateConfig(DeepLearningConfigState nextState) {
    setState(() {
      _config = nextState;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _viewModel,
      builder: (context, _) {
        return Scaffold(
          extendBodyBehindAppBar: true,
          appBar: AppBar(
            title: const Text('深度学习实验室'),
            backgroundColor: Colors.transparent,
            elevation: 0,
            flexibleSpace: Opacity(
              opacity: 0.8,
              child: Container(
                decoration: const BoxDecoration(
                  gradient: AppColors.deepLearningGradient,
                ),
              ),
            ),
          ),
          body: Container(
            decoration: const BoxDecoration(
              gradient: AppColors.backgroundGradient,
            ),
            child: SafeArea(
              child: ResponsiveWrapper(
                child: SingleChildScrollView(
                  padding: ResponsiveHelper.getPagePadding(context),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const DeepLearningHeader(),
                      const SizedBox(height: 24),
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final stacked =
                              constraints.maxWidth <
                              ResponsiveHelper.tabletBreakpoint;

                          final configPanel = DeepLearningConfigPanel(
                            config: _config,
                            isTraining: _isTraining,
                            onModelTypeChanged: (value) {
                              _updateConfig(_config.copyWith(modelType: value));
                            },
                            onEpochsChanged: (value) {
                              _updateConfig(_config.copyWith(epochs: value));
                            },
                            onWindowSizeChanged: (value) {
                              _updateConfig(
                                _config.copyWith(windowSize: value),
                              );
                            },
                            onBatchSizeChanged: (value) {
                              _updateConfig(_config.copyWith(batchSize: value));
                            },
                            onStartTraining: _startTraining,
                          );

                          final terminalPanel = DeepLearningTerminalPanel(
                            isTraining: _isTraining,
                            logs: _trainLogs,
                          );

                          if (stacked) {
                            return Column(
                              key: const ValueKey('deep-learning-layout-column'),
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                configPanel,
                                const SizedBox(height: 16),
                                terminalPanel,
                              ],
                            );
                          }

                          return Row(
                            key: const ValueKey('deep-learning-layout-row'),
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(flex: 4, child: configPanel),
                              const SizedBox(width: 24),
                              Expanded(flex: 6, child: terminalPanel),
                            ],
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
