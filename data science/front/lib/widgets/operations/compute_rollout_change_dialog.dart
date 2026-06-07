/// Compute rollout change confirmation dialog.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/compute_rollout_policy.dart';

class ComputeRolloutChangeDraft {
  const ComputeRolloutChangeDraft({
    required this.changeReason,
    required this.requestKind,
    required this.targetPolicy,
  });

  final String changeReason;
  final String requestKind;
  final Map<String, dynamic> targetPolicy;
}

Future<ComputeRolloutChangeDraft?> showComputeRolloutChangeDialog(
  BuildContext context, {
  required ComputeRolloutComponentPolicy component,
  required String targetRolloutMode,
}) {
  return showDialog<ComputeRolloutChangeDraft>(
    context: context,
    builder: (dialogContext) {
      return _ComputeRolloutChangeDialog(
        component: component,
        targetRolloutMode: targetRolloutMode,
      );
    },
  );
}

class _ComputeRolloutChangeDialog extends StatefulWidget {
  const _ComputeRolloutChangeDialog({
    required this.component,
    required this.targetRolloutMode,
  });

  final ComputeRolloutComponentPolicy component;
  final String targetRolloutMode;

  @override
  State<_ComputeRolloutChangeDialog> createState() =>
      _ComputeRolloutChangeDialogState();
}

class _ComputeRolloutChangeDialogState
    extends State<_ComputeRolloutChangeDialog> {
  late final TextEditingController _reasonController;
  late double _canaryPercent;

  bool get _isRollback =>
      widget.targetRolloutMode == _stableModeForComponent(widget.component.key);

  bool get _requiresApproval =>
      widget.component.key == 'feature_engineering' &&
      (widget.targetRolloutMode == 'native_candidate' ||
          widget.targetRolloutMode == 'native_enforced');

  @override
  void initState() {
    super.initState();
    _reasonController = TextEditingController();
    _canaryPercent = _initialCanaryPercent().toDouble();
  }

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final allowsCanaryControl =
        widget.component.key == 'feature_engineering' &&
        widget.targetRolloutMode == 'native_candidate';
    return AlertDialog(
      title: Text('${widget.component.label} rollout 变更'),
      content: SizedBox(
        width: 460,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '当前模式 · ${_rolloutLabel(widget.component.rolloutMode)}',
              style: AppTextStyles.bodyMedium,
            ),
            const SizedBox(height: 6),
            Text(
              '目标模式 · ${_rolloutLabel(widget.targetRolloutMode)}',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _requiresApproval
                    ? AppColors.warningLight
                    : AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Text(
                _requiresApproval
                    ? '该变更将进入审批队列，批准后才会真正应用。'
                    : _isRollback
                    ? '该变更会生成一条回退运行，用于恢复稳定路径。'
                    : '该变更会生成一条治理运行，并进入统一 Operation 时间线。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: _requiresApproval
                      ? AppColors.warning
                      : AppColors.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (allowsCanaryControl) ...[
              Text(
                'Canary 流量 · ${_canaryPercent.round()}%',
                style: AppTextStyles.bodyMedium,
              ),
              Slider(
                value: _canaryPercent,
                min: 5,
                max: 100,
                divisions: 19,
                label: '${_canaryPercent.round()}%',
                onChanged: (value) {
                  setState(() {
                    _canaryPercent = value;
                  });
                },
              ),
              Text(
                _canaryPercent.round() >= 100
                    ? '100% 流量都将命中 Native 路径。'
                    : '仅有 ${_canaryPercent.round()}% 的命中桶会进入 Native 灰度。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 12),
            ],
            TextField(
              controller: _reasonController,
              minLines: 3,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: '变更说明',
                hintText: '可选，写明变更原因、窗口期或回退背景',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('取消'),
        ),
        FilledButton.icon(
          onPressed: () {
            Navigator.of(context).pop(
              ComputeRolloutChangeDraft(
                changeReason: _reasonController.text.trim(),
                requestKind: _isRollback ? 'rollback' : 'rollout_change',
                targetPolicy: _buildTargetPolicy(),
              ),
            );
          },
          icon: Icon(
            _isRollback ? Icons.restore_rounded : Icons.rocket_launch_rounded,
          ),
          label: Text(_isRollback ? '提交回退' : '提交变更'),
        ),
      ],
    );
  }

  int _initialCanaryPercent() {
    if (widget.component.key != 'feature_engineering') {
      return widget.component.canaryPercent;
    }
    if (widget.targetRolloutMode != 'native_candidate') {
      return widget.targetRolloutMode == 'native_enforced' ? 100 : 0;
    }
    final current = widget.component.canaryPercent;
    if (widget.component.rolloutMode == 'native_candidate' && current > 0) {
      return current;
    }
    return 10;
  }

  Map<String, dynamic> _buildTargetPolicy() {
    final targetPolicy = <String, dynamic>{
      'rollout_mode': widget.targetRolloutMode,
    };

    if (widget.component.key == 'feature_engineering') {
      if (widget.targetRolloutMode == 'native_candidate') {
        targetPolicy['canary_percent'] = _canaryPercent.round();
      } else if (widget.targetRolloutMode == 'native_enforced') {
        targetPolicy['canary_percent'] = 100;
      } else if (widget.targetRolloutMode == 'python_stable') {
        targetPolicy['canary_percent'] = 0;
      }
    }
    return targetPolicy;
  }
}

String _stableModeForComponent(String componentKey) {
  switch (componentKey) {
    case 'feature_engineering':
      return 'python_stable';
    case 'scenario_simulation':
      return 'vectorized_python';
    default:
      return '';
  }
}

String _rolloutLabel(String mode) {
  switch (mode) {
    case 'python_stable':
      return '稳定 Python';
    case 'native_candidate':
      return '灰度 Native';
    case 'native_enforced':
      return '强制 Native';
    case 'python_loop':
      return '逐场景循环';
    case 'vectorized_python':
      return '向量化';
    default:
      return mode;
  }
}
