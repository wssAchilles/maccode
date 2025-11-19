/// 分析详情页面 - 展示完整的历史分析结果
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../widgets/analysis/quality_dashboard.dart';
import '../widgets/analysis/correlation_matrix_view.dart';
import '../widgets/analysis/statistical_panel.dart';

class AnalysisDetailScreen extends StatelessWidget {
  final Map<String, dynamic> record;

  const AnalysisDetailScreen({
    super.key,
    required this.record,
  });

  @override
  Widget build(BuildContext context) {
    final summary = record['summary'] as Map<String, dynamic>?;
    final filename = record['filename'] ?? '未知文件';
    final createdAt = record['created_at'];
    
    DateTime? dateTime;
    if (createdAt != null) {
      if (createdAt is String) {
        dateTime = DateTime.tryParse(createdAt);
      } else if (createdAt is Map && createdAt['_seconds'] != null) {
        dateTime = DateTime.fromMillisecondsSinceEpoch(
          createdAt['_seconds'] * 1000,
        );
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(filename),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: summary == null
          ? _buildNoDataView()
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 文件信息卡片
                  _buildFileInfoCard(filename, dateTime, summary),
                  const SizedBox(height: 24),

                  // 数据质量仪表板
                  if (summary['quality_analysis'] != null &&
                      summary['quality_analysis']['success'] == true) ...[
                    _buildSectionTitle('数据质量评估', Icons.assessment),
                    const SizedBox(height: 12),
                    _buildQualitySection(summary['quality_analysis']),
                    const SizedBox(height: 24),
                  ],

                  // 相关性分析
                  if (summary['correlation_analysis'] != null &&
                      summary['correlation_analysis']['success'] == true) ...[
                    _buildSectionTitle('相关性分析', Icons.scatter_plot),
                    const SizedBox(height: 12),
                    _buildCorrelationSection(summary['correlation_analysis']),
                    const SizedBox(height: 24),
                  ],

                  // 统计检验
                  if (summary['statistical_tests'] != null &&
                      summary['statistical_tests']['success'] == true) ...[
                    _buildSectionTitle('统计检验', Icons.functions),
                    const SizedBox(height: 12),
                    _buildStatisticalSection(summary['statistical_tests']),
                    const SizedBox(height: 24),
                  ],

                  // 基本信息
                  if (summary['basic_info'] != null) ...[
                    _buildSectionTitle('数据集信息', Icons.info_outline),
                    const SizedBox(height: 12),
                    _buildBasicInfoSection(summary['basic_info']),
                    const SizedBox(height: 24),
                  ],

                  // 数据预览
                  if (summary['preview'] != null) ...[
                    _buildSectionTitle('数据预览', Icons.table_chart),
                    const SizedBox(height: 12),
                    _buildDataPreview(summary['preview']),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildNoDataView() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text(
            '无可用数据',
            style: TextStyle(fontSize: 18, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _buildFileInfoCard(String filename, DateTime? dateTime, Map<String, dynamic> summary) {
    final basicInfo = summary['basic_info'] as Map<String, dynamic>?;
    final qualityAnalysis = summary['quality_analysis'] as Map<String, dynamic>?;
    final qualityScore = qualityAnalysis?['quality_score'] as num?;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.insert_drive_file, size: 32, color: Colors.blue),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        filename,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (dateTime != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          '分析时间: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(dateTime)}',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (qualityScore != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: _getQualityColor(qualityScore.toDouble()),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${qualityScore.toStringAsFixed(1)}分',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            if (basicInfo != null) ...[
              const Divider(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildInfoItem(
                    Icons.table_rows,
                    '行数',
                    basicInfo['rows']?.toString() ?? '-',
                  ),
                  _buildInfoItem(
                    Icons.view_column,
                    '列数',
                    basicInfo['columns']?.toString() ?? '-',
                  ),
                  _buildInfoItem(
                    Icons.memory,
                    '内存',
                    basicInfo['memory_usage'] ?? '-',
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildInfoItem(IconData icon, String label, String value) {
    return Column(
      children: [
        Icon(icon, size: 24, color: Colors.blue),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildSectionTitle(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 24, color: Colors.blue),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildQualitySection(Map<String, dynamic> qualityAnalysis) {
    final qualityScore = qualityAnalysis['quality_score'] as num?;
    final qualityMetrics = qualityAnalysis['quality_metrics'] as Map<String, dynamic>?;
    final recommendations = qualityAnalysis['recommendations'] as List?;
    final highRiskColumns = qualityAnalysis['high_risk_columns'] as List?;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 质量评分
            if (qualityScore != null) ...[
              Center(
                child: Column(
                  children: [
                    SizedBox(
                      width: 120,
                      height: 120,
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          SizedBox(
                            width: 120,
                            height: 120,
                            child: CircularProgressIndicator(
                              value: qualityScore / 100,
                              strokeWidth: 12,
                              backgroundColor: Colors.grey.shade200,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                _getQualityColor(qualityScore.toDouble()),
                              ),
                            ),
                          ),
                          Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                qualityScore.toStringAsFixed(1),
                                style: const TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Text(
                                '/ 100',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _getQualityLabel(qualityScore.toDouble()),
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: _getQualityColor(qualityScore.toDouble()),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],

            // 质量指标
            if (qualityMetrics != null) ...[
              const Text(
                '质量指标',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              _buildMetricRow('缺失率', '${qualityMetrics['missing_rate']?.toStringAsFixed(2) ?? '-'}%'),
              _buildMetricRow('异常值数量', qualityMetrics['total_outliers']?.toString() ?? '-'),
              _buildMetricRow('重复行数', qualityMetrics['duplicate_rows']?.toString() ?? '-'),
              const SizedBox(height: 16),
            ],

            // 高风险列
            if (highRiskColumns != null && highRiskColumns.isNotEmpty) ...[
              const Text(
                '高风险列',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: highRiskColumns.map((col) {
                  return Chip(
                    label: Text(col.toString()),
                    backgroundColor: Colors.orange.shade100,
                    labelStyle: const TextStyle(color: Colors.orange),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],

            // 建议
            if (recommendations != null && recommendations.isNotEmpty) ...[
              const Text(
                '优化建议',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              ...recommendations.map((rec) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.lightbulb_outline, size: 20, color: Colors.amber),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          rec.toString(),
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCorrelationSection(Map<String, dynamic> correlationAnalysis) {
    final highCorrelations = correlationAnalysis['high_correlations'] as List?;
    final suggestions = correlationAnalysis['suggestions'] as List?;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 高相关性对
            if (highCorrelations != null && highCorrelations.isNotEmpty) ...[
              const Text(
                '高相关性变量对',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              ...highCorrelations.map((pair) {
                final col1 = pair['column1'];
                final col2 = pair['column2'];
                final correlation = pair['correlation'] as num?;
                
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          '$col1 ↔ $col2',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _getCorrelationColor(correlation?.toDouble() ?? 0),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          correlation?.toStringAsFixed(3) ?? '-',
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
              const SizedBox(height: 16),
            ],

            // 建议
            if (suggestions != null && suggestions.isNotEmpty) ...[
              const Text(
                '分析建议',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              ...suggestions.map((sug) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.tips_and_updates, size: 20, color: Colors.blue),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          sug.toString(),
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatisticalSection(Map<String, dynamic> statisticalTests) {
    final normalityTests = statisticalTests['normality_tests'] as Map<String, dynamic>?;
    final nonNormalColumns = statisticalTests['non_normal_columns'] as List?;
    final suggestions = statisticalTests['suggestions'] as List?;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 正态性检验结果
            if (normalityTests != null && normalityTests.isNotEmpty) ...[
              const Text(
                '正态性检验',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              ...normalityTests.entries.map((entry) {
                final columnName = entry.key;
                final testResult = entry.value as Map<String, dynamic>?;
                final isNormal = testResult?['is_normal'] as bool? ?? false;
                final pValue = testResult?['p_value'] as num?;
                final skewness = testResult?['skewness'] as num?;
                final kurtosis = testResult?['kurtosis'] as num?;

                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isNormal ? Colors.green.shade50 : Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isNormal ? Colors.green.shade200 : Colors.orange.shade200,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            isNormal ? Icons.check_circle : Icons.warning,
                            color: isNormal ? Colors.green : Colors.orange,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              columnName,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          Text(
                            isNormal ? '正态分布' : '非正态分布',
                            style: TextStyle(
                              fontSize: 12,
                              color: isNormal ? Colors.green : Colors.orange,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildStatItem('P值', pValue?.toStringAsFixed(4) ?? '-'),
                          _buildStatItem('偏度', skewness?.toStringAsFixed(3) ?? '-'),
                          _buildStatItem('峰度', kurtosis?.toStringAsFixed(3) ?? '-'),
                        ],
                      ),
                    ],
                  ),
                );
              }).toList(),
              const SizedBox(height: 16),
            ],

            // 非正态列
            if (nonNormalColumns != null && nonNormalColumns.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.orange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${nonNormalColumns.length} 列不符合正态分布',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // 建议
            if (suggestions != null && suggestions.isNotEmpty) ...[
              const Text(
                '统计建议',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              ...suggestions.map((sug) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.auto_awesome, size: 20, color: Colors.purple),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          sug.toString(),
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildBasicInfoSection(Map<String, dynamic> basicInfo) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildMetricRow('数据行数', basicInfo['rows']?.toString() ?? '-'),
            _buildMetricRow('数据列数', basicInfo['columns']?.toString() ?? '-'),
            _buildMetricRow('内存使用', basicInfo['memory_usage'] ?? '-'),
            if (basicInfo['column_types'] != null) ...[
              const SizedBox(height: 12),
              const Text(
                '列类型',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              ...(basicInfo['column_types'] as Map).entries.map((entry) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          entry.key.toString(),
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                      Chip(
                        label: Text(
                          entry.value.toString(),
                          style: const TextStyle(fontSize: 11),
                        ),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ],
                  ),
                );
              }).toList(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDataPreview(Map<String, dynamic> preview) {
    final columns = preview['columns'] as List?;
    final data = preview['data'] as List?;

    if (columns == null || data == null || columns.isEmpty || data.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16.0),
          child: Text('无数据预览'),
        ),
      );
    }

    return Card(
      elevation: 2,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: DataTable(
            columns: columns.map((col) {
              return DataColumn(
                label: Text(
                  col.toString(),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              );
            }).toList(),
            rows: data.take(10).map((row) {
              final rowData = row as List;
              return DataRow(
                cells: rowData.map((cell) {
                  return DataCell(
                    Text(
                      cell?.toString() ?? '',
                      style: const TextStyle(fontSize: 13),
                    ),
                  );
                }).toList(),
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildMetricRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade700,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Color _getQualityColor(double score) {
    if (score >= 90) return Colors.green;
    if (score >= 70) return Colors.orange;
    return Colors.red;
  }

  String _getQualityLabel(double score) {
    if (score >= 90) return '优秀';
    if (score >= 70) return '良好';
    if (score >= 50) return '一般';
    return '较差';
  }

  Color _getCorrelationColor(double correlation) {
    final abs = correlation.abs();
    if (abs >= 0.7) return Colors.red;
    if (abs >= 0.5) return Colors.orange;
    return Colors.blue;
  }
}
