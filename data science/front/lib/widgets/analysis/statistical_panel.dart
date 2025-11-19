/// 统计检验面板组件
/// 显示正态性检验结果
library;

import 'package:flutter/material.dart';
import '../../models/analysis_result.dart';

class StatisticalPanel extends StatelessWidget {
  final StatisticalResult statisticalResult;

  const StatisticalPanel({
    super.key,
    required this.statisticalResult,
  });

  @override
  Widget build(BuildContext context) {
    // 如果分析失败，显示错误
    if (!statisticalResult.success) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.orange),
              const SizedBox(height: 8),
              Text(
                '统计检验不可用',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                statisticalResult.message ?? '没有数值列或出现错误',
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
                const Icon(Icons.analytics, size: 28),
                const SizedBox(width: 8),
                Text(
                  '统计检验',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 摘要统计
            if (statisticalResult.summary != null)
              _buildSummary(context, statisticalResult.summary!),

            const SizedBox(height: 16),

            // 建议
            if (statisticalResult.suggestions != null &&
                statisticalResult.suggestions!.isNotEmpty)
              _buildSuggestions(context, statisticalResult.suggestions!),

            const SizedBox(height: 16),

            // 正态性检验表格
            if (statisticalResult.normalityTests != null &&
                statisticalResult.normalityTests!.isNotEmpty)
              _buildNormalityTable(context, statisticalResult.normalityTests!),
          ],
        ),
      ),
    );
  }

  /// 构建摘要统计
  Widget _buildSummary(BuildContext context, TestSummary summary) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildSummaryItem(
            context,
            Icons.functions,
            '总列数',
            summary.totalNumericColumns.toString(),
            Colors.blue,
          ),
          Container(
            width: 1,
            height: 40,
            color: Colors.grey.shade300,
          ),
          _buildSummaryItem(
            context,
            Icons.check_circle,
            '正态分布',
            summary.normalDistributionCount.toString(),
            Colors.green,
          ),
          Container(
            width: 1,
            height: 40,
            color: Colors.grey.shade300,
          ),
          _buildSummaryItem(
            context,
            Icons.warning,
            '非正态',
            summary.nonNormalDistributionCount.toString(),
            Colors.orange,
          ),
        ],
      ),
    );
  }

  /// 构建单个摘要项
  Widget _buildSummaryItem(
    BuildContext context,
    IconData icon,
    String label,
    String value,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  /// 构建建议
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
              Icon(Icons.lightbulb_outline, color: Colors.blue.shade700),
              const SizedBox(width: 8),
              Text(
                '方法建议',
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

  /// 构建正态性检验表格
  Widget _buildNormalityTable(
    BuildContext context,
    Map<String, NormalityTest> tests,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '正态性检验详情',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStateProperty.all(Colors.grey.shade100),
            dataRowMinHeight: 48,
            dataRowMaxHeight: 64,
            columns: const [
              DataColumn(
                label: Text(
                  '变量名',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '检验方法',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  'p-value',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '结果',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '偏度',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '峰度',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              DataColumn(
                label: Text(
                  '样本数',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
            rows: tests.entries.map((entry) {
              final columnName = entry.key;
              final test = entry.value;

              // 如果有错误
              if (test.error != null) {
                return DataRow(
                  cells: [
                    DataCell(Text(columnName)),
                    DataCell(Text(test.error!, style: const TextStyle(color: Colors.red))),
                    const DataCell(Text('-')),
                    const DataCell(Text('-')),
                    const DataCell(Text('-')),
                    const DataCell(Text('-')),
                    const DataCell(Text('-')),
                  ],
                );
              }

              final isNormal = test.isNormal ?? false;
              final rowColor = isNormal ? null : Colors.red.shade50;

              return DataRow(
                color: WidgetStateProperty.all(rowColor),
                cells: [
                  DataCell(
                    Text(
                      columnName,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
                  DataCell(Text(test.testName ?? '-')),
                  DataCell(
                    Text(
                      test.pValue != null
                          ? (test.pValue! < 0.001
                              ? '<0.001'
                              : test.pValue!.toStringAsFixed(4))
                          : '-',
                      style: TextStyle(
                        color: (test.pValue ?? 1.0) < 0.05 ? Colors.red : Colors.green,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isNormal
                            ? Colors.green.withOpacity(0.2)
                            : Colors.red.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isNormal ? Colors.green : Colors.red,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            isNormal ? Icons.check : Icons.close,
                            size: 16,
                            color: isNormal ? Colors.green : Colors.red,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            test.distribution ?? '-',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: isNormal ? Colors.green : Colors.red,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      test.skewness != null
                          ? test.skewness!.toStringAsFixed(2)
                          : '-',
                      style: TextStyle(
                        color: (test.skewness?.abs() ?? 0) > 1
                            ? Colors.orange
                            : Colors.black,
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      test.kurtosis != null
                          ? test.kurtosis!.toStringAsFixed(2)
                          : '-',
                    ),
                  ),
                  DataCell(Text(test.nSamples?.toString() ?? '-')),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
