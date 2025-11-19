/// 相关性矩阵视图组件
/// 移动端显示文字列表，桌面端显示表格/热力图
library;

import 'package:flutter/material.dart';
import '../../models/analysis_result.dart';

class CorrelationMatrixView extends StatelessWidget {
  final CorrelationResult correlationResult;
  final bool isMobile;

  const CorrelationMatrixView({
    super.key,
    required this.correlationResult,
    this.isMobile = false,
  });

  @override
  Widget build(BuildContext context) {
    // 如果分析失败，显示错误
    if (!correlationResult.success) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.orange),
              const SizedBox(height: 8),
              Text(
                '相关性分析不可用',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                correlationResult.message ?? '数据列不足或出现错误',
                style: const TextStyle(color: Colors.grey),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                const Icon(Icons.hub, size: 28),
                const SizedBox(width: 8),
                Text(
                  '相关性分析',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 显示建议
            if (correlationResult.suggestions != null &&
                correlationResult.suggestions!.isNotEmpty)
              _buildSuggestions(context, correlationResult.suggestions!),

            const SizedBox(height: 16),

            // 高相关性变量对
            if (correlationResult.highCorrelations != null &&
                correlationResult.highCorrelations!.isNotEmpty) ...[
              _buildHighCorrelationsSection(context),
              const SizedBox(height: 16),
            ],

            // 根据屏幕大小显示不同布局
            if (isMobile)
              _buildMobileView(context)
            else
              _buildDesktopView(context),
          ],
        ),
      ),
    );
  }

  /// 构建建议部分
  Widget _buildSuggestions(BuildContext context, List<String> suggestions) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, color: Colors.blue.shade700),
              const SizedBox(width: 8),
              Text(
                '分析建议',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.blue.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...suggestions.map((suggestion) => Padding(
                padding: const EdgeInsets.only(top: 4.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• ', style: TextStyle(fontSize: 16)),
                    Expanded(
                      child: Text(
                        suggestion,
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  /// 构建高相关性部分
  Widget _buildHighCorrelationsSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.orange.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber, color: Colors.orange.shade700),
              const SizedBox(width: 8),
              Text(
                '高相关性变量 (|r| > 0.7)',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.orange.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...correlationResult.highCorrelations!.map((hc) => Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${hc.variables[0]} ↔️ ${hc.variables[1]}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w500,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: _getCorrelationColor(hc.correlation).withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _getCorrelationColor(hc.correlation),
                        ),
                      ),
                      child: Text(
                        'r = ${hc.correlation.toStringAsFixed(3)}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                          color: _getCorrelationColor(hc.correlation),
                        ),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  /// 移动端视图：列表展示
  Widget _buildMobileView(BuildContext context) {
    if (correlationResult.correlations == null ||
        correlationResult.correlations!.isEmpty) {
      return const Center(
        child: Text('没有足够的数值列进行相关性分析'),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '相关系数详情',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        ...correlationResult.correlations!
            .where((pair) => pair.error == null)
            .map((pair) => _buildCorrelationCard(context, pair)),
      ],
    );
  }

  /// 桌面端视图：表格展示
  Widget _buildDesktopView(BuildContext context) {
    if (correlationResult.correlations == null ||
        correlationResult.correlations!.isEmpty) {
      return const Center(
        child: Text('没有足够的数值列进行相关性分析'),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowColor: WidgetStateProperty.all(Colors.grey.shade100),
        columns: const [
          DataColumn(label: Text('变量 X', style: TextStyle(fontWeight: FontWeight.bold))),
          DataColumn(label: Text('变量 Y', style: TextStyle(fontWeight: FontWeight.bold))),
          DataColumn(label: Text('Pearson r', style: TextStyle(fontWeight: FontWeight.bold))),
          DataColumn(label: Text('p-value', style: TextStyle(fontWeight: FontWeight.bold))),
          DataColumn(label: Text('Spearman ρ', style: TextStyle(fontWeight: FontWeight.bold))),
          DataColumn(label: Text('样本数', style: TextStyle(fontWeight: FontWeight.bold))),
        ],
        rows: correlationResult.correlations!
            .where((pair) => pair.error == null)
            .map((pair) => DataRow(
                  cells: [
                    DataCell(Text(pair.variableX)),
                    DataCell(Text(pair.variableY)),
                    DataCell(
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _getCorrelationColor(pair.pearson.correlation)
                              .withOpacity(0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          pair.pearson.correlation.toStringAsFixed(3),
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: _getCorrelationColor(pair.pearson.correlation),
                          ),
                        ),
                      ),
                    ),
                    DataCell(
                      Text(
                        pair.pearson.pValue < 0.001
                            ? '<0.001'
                            : pair.pearson.pValue.toStringAsFixed(3),
                        style: TextStyle(
                          color: pair.pearson.significant ? Colors.green : Colors.grey,
                          fontWeight:
                              pair.pearson.significant ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ),
                    DataCell(
                      Text(
                        pair.spearman.correlation.toStringAsFixed(3),
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ),
                    DataCell(Text(pair.nSamples.toString())),
                  ],
                ))
            .toList(),
      ),
    );
  }

  /// 构建单个相关性卡片（移动端）
  Widget _buildCorrelationCard(BuildContext context, CorrelationPair pair) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${pair.variableX} ↔️ ${pair.variableY}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ),
                if (pair.pearson.significant)
                  const Icon(Icons.check_circle, color: Colors.green, size: 20),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildCoefficient(
                    'Pearson',
                    pair.pearson.correlation,
                    pair.pearson.pValue,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildCoefficient(
                    'Spearman',
                    pair.spearman.correlation,
                    pair.spearman.pValue,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '样本数: ${pair.nSamples}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建系数显示
  Widget _buildCoefficient(String label, double correlation, double pValue) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: _getCorrelationColor(correlation).withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _getCorrelationColor(correlation).withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'r = ${correlation.toStringAsFixed(3)}',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: _getCorrelationColor(correlation),
            ),
          ),
          Text(
            'p ${pValue < 0.001 ? '<0.001' : '=${pValue.toStringAsFixed(3)}'}',
            style: const TextStyle(fontSize: 11, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  /// 根据相关系数获取颜色
  Color _getCorrelationColor(double correlation) {
    final absCorr = correlation.abs();
    if (absCorr >= 0.7) return Colors.red;
    if (absCorr >= 0.4) return Colors.orange;
    return Colors.blue;
  }
}
