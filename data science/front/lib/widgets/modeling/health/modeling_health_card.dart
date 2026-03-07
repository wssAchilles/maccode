part of '../modeling_health_section.dart';

class ModelingHealthCard extends StatelessWidget {
  const ModelingHealthCard({super.key, required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 6,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.purple[200]!, width: 2),
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Colors.purple[50]!, Colors.blue[50]!],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _ModelingHealthHeader(modelInfo: modelInfo),
              const SizedBox(height: 20),
              _ModelingHealthMetricsPanel(modelInfo: modelInfo),
              const SizedBox(height: 16),
              _ModelingHealthPrimaryStats(modelInfo: modelInfo),
              if (modelInfo.usedAutoSelection) ...[
                const SizedBox(height: 16),
                _AutoSelectionCard(modelInfo: modelInfo),
              ],
              if (modelInfo.trainingConfig != null) ...[
                const SizedBox(height: 16),
                _OptimizationConfigCard(modelInfo: modelInfo),
              ],
              if (modelInfo.validationSummary != null ||
                  modelInfo.dataCoverage != null) ...[
                const SizedBox(height: 16),
                _ValidationSummaryCard(modelInfo: modelInfo),
              ],
              const SizedBox(height: 16),
              _ModelDataSourceCard(modelInfo: modelInfo),
            ],
          ),
        ),
      ),
    );
  }
}

class _ModelingHealthHeader extends StatelessWidget {
  const _ModelingHealthHeader({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.purple[600],
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.psychology, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 12),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '🧠 AI 模型状态',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              Text(
                '机器学习预测引擎（眼睛）',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: modelInfo.isValid ? Colors.green : Colors.orange,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            modelInfo.isValid ? '运行中' : '待训练',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
}

class _ModelingHealthMetricsPanel extends StatelessWidget {
  const _ModelingHealthMetricsPanel({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    final metrics = modelInfo.metrics;
    if (metrics == null) {
      return const Center(
        child: Padding(padding: EdgeInsets.all(16), child: Text('暂无详细性能指标')),
      );
    }

    final r2Score = (metrics.r2Score ?? 0).clamp(0.0, 1.0);
    final mape = metrics.mape ?? 0;
    final accuracyColor = mape < 0.1 ? Colors.green : Colors.orange;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              children: [
                CircularPercentIndicator(
                  radius: 40,
                  lineWidth: 8,
                  percent: r2Score,
                  center: Text(
                    '${(r2Score * 100).toStringAsFixed(0)}%',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.purple[700],
                    ),
                  ),
                  progressColor: r2Score > 0.8 ? Colors.green : Colors.orange,
                  backgroundColor: Colors.purple[50]!,
                  circularStrokeCap: CircularStrokeCap.round,
                  animation: true,
                ),
                const SizedBox(height: 8),
                Text(
                  'R² Score',
                  style: TextStyle(
                    color: Colors.grey[700],
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'MAPE (误差)',
                      style: TextStyle(
                        color: Colors.grey[700],
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      '${(mape * 100).toStringAsFixed(1)}%',
                      style: TextStyle(
                        color: accuracyColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                LinearPercentIndicator(
                  lineHeight: 8,
                  percent: (1.0 - mape).clamp(0.0, 1.0),
                  progressColor: accuracyColor,
                  backgroundColor: Colors.purple[50]!,
                  barRadius: const Radius.circular(4),
                  animation: true,
                ),
                const SizedBox(height: 4),
                Text(
                  mape < 0.1 ? '精度优良' : '精度一般',
                  style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModelingHealthPrimaryStats extends StatelessWidget {
  const _ModelingHealthPrimaryStats({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.model_training,
                label: '模型类型',
                value: modelInfo.usedAutoSelection
                    ? modelInfo.winnerModel
                    : 'Random Forest',
                color: Colors.blue[700]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.storage,
                label: '训练数据',
                value: modelInfo.trainingSamples != null
                    ? '${modelInfo.trainingSamples} 样本'
                    : 'N/A',
                color: Colors.green[700]!,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ModelingStatItem(
                icon: Icons.schedule,
                label: '最近更新',
                value: modelInfo.trainedAtFormatted,
                color: Colors.orange[700]!,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ModelingStatItem(
                icon: Icons.precision_manufacturing,
                label: '预测精度 (MAE)',
                value: modelInfo.maeFormatted,
                color: Colors.purple[700]!,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ModelDataSourceCard extends StatelessWidget {
  const _ModelDataSourceCard({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue[50],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.cloud_download, color: Colors.blue[700], size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '数据来源: ${modelInfo.dataSource ?? "CAISO 实时流"}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Colors.blue[900],
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '模型每日凌晨自动重训，持续学习最新用电模式',
                  style: TextStyle(fontSize: 11, color: Colors.blue[700]),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
