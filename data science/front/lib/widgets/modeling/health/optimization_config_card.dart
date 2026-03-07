part of '../modeling_health_section.dart';

class _OptimizationConfigCard extends StatelessWidget {
  const _OptimizationConfigCard({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    final config = modelInfo.trainingConfig!;

    return Container(
      key: const ValueKey('modeling-training-config-card'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.indigo[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.indigo[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.tune, color: Colors.indigo[700], size: 18),
              const SizedBox(width: 8),
              Text(
                '⚙️ 训练配置',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.indigo[900],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ConfigChip(
                label: 'Log1p 变换',
                enabled: config.useLogTransform ?? false,
                icon: Icons.functions,
              ),
              _ConfigChip(
                label: '异常值剔除',
                enabled: config.removeOutliers ?? false,
                icon: Icons.filter_alt,
              ),
              _ConfigChip(
                label: '超参数调优',
                enabled: config.tuneHyperparameters ?? false,
                icon: Icons.explore,
              ),
              _ConfigChip(
                label: '时序交叉验证',
                enabled: config.useTimeSeriesCV ?? false,
                icon: Icons.timeline,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConfigChip extends StatelessWidget {
  const _ConfigChip({
    required this.label,
    required this.enabled,
    required this.icon,
  });

  final String label;
  final bool enabled;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: enabled ? Colors.white : Colors.grey[200],
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: enabled ? Colors.indigo[200]! : Colors.grey[300]!,
        ),
        boxShadow: enabled
            ? [
                BoxShadow(
                  color: Colors.indigo.withValues(alpha: 0.1),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: enabled ? Colors.indigo[600] : Colors.grey[500],
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: enabled ? FontWeight.bold : FontWeight.normal,
              color: enabled ? Colors.indigo[800] : Colors.grey[600],
            ),
          ),
          const SizedBox(width: 4),
          Icon(
            enabled ? Icons.check_circle : Icons.cancel,
            size: 14,
            color: enabled ? Colors.green[600] : Colors.grey[400],
          ),
        ],
      ),
    );
  }
}
