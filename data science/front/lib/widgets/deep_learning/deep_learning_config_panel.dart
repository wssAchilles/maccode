/// 深度学习页面训练配置组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/deep_learning_config_state.dart';
import '../common/animated_glass_card.dart';

class DeepLearningConfigPanel extends StatelessWidget {
  const DeepLearningConfigPanel({
    super.key,
    required this.config,
    required this.isTraining,
    required this.onModelTypeChanged,
    required this.onEpochsChanged,
    required this.onWindowSizeChanged,
    required this.onBatchSizeChanged,
    required this.onStartTraining,
  });

  final DeepLearningConfigState config;
  final bool isTraining;
  final ValueChanged<DeepLearningModelType> onModelTypeChanged;
  final ValueChanged<int> onEpochsChanged;
  final ValueChanged<int> onWindowSizeChanged;
  final ValueChanged<int> onBatchSizeChanged;
  final VoidCallback onStartTraining;

  static const List<int> batchSizeOptions = <int>[16, 32, 64, 128];

  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('模型配置', style: AppTextStyles.h4),
          const SizedBox(height: 20),
          _buildDropdown<DeepLearningModelType>(
            key: const ValueKey('deep-learning-model-type'),
            label: '模型结构',
            value: config.modelType,
            items: DeepLearningModelType.values,
            itemLabel: (value) => value.name,
            onChanged: isTraining ? null : onModelTypeChanged,
          ),
          const SizedBox(height: 16),
          _buildSlider(
            label: '训练轮次',
            value: config.epochs.toDouble(),
            min: 10,
            max: 200,
            onChanged: isTraining
                ? null
                : (value) => onEpochsChanged(value.toInt()),
          ),
          _buildSlider(
            label: '回看窗口',
            value: config.windowSize.toDouble(),
            min: 12,
            max: 168,
            onChanged: isTraining
                ? null
                : (value) => onWindowSizeChanged(value.toInt()),
          ),
          _buildDropdown<int>(
            key: const ValueKey('deep-learning-batch-size'),
            label: '批大小',
            value: config.batchSize,
            items: batchSizeOptions,
            itemLabel: (value) => value.toString(),
            onChanged: isTraining ? null : onBatchSizeChanged,
          ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              key: const ValueKey('deep-learning-run-button'),
              onPressed: isTraining ? null : onStartTraining,
              icon: isTraining
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.play_arrow_rounded),
              label: Text(
                isTraining
                    ? '训练进行中...'
                    : '启动云端训练',
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF8B5CF6),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown<T>({
    required Key key,
    required String label,
    required T value,
    required List<T> items,
    required String Function(T value) itemLabel,
    required ValueChanged<T>? onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.labelMedium),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<T>(
              key: key,
              value: value,
              isExpanded: true,
              items: items
                  .map(
                    (item) => DropdownMenuItem<T>(
                      value: item,
                      child: Text(itemLabel(item)),
                    ),
                  )
                  .toList(),
              onChanged: onChanged == null
                  ? null
                  : (value) {
                      if (value != null) {
                        onChanged(value);
                      }
                    },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSlider({
    required String label,
    required double value,
    required double min,
    required double max,
    required ValueChanged<double>? onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTextStyles.labelMedium),
            Text(
              value.toInt().toString(),
              style: AppTextStyles.labelLarge.copyWith(
                color: AppColors.primary,
              ),
            ),
          ],
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          activeColor: const Color(0xFF8B5CF6),
          onChanged: onChanged,
        ),
      ],
    );
  }
}
