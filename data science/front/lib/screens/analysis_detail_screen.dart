/// 分析详情页面 - 展示完整的历史分析结果
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/history_record.dart';
import '../widgets/history/analysis_detail_sections.dart';

class AnalysisDetailScreen extends StatelessWidget {
  const AnalysisDetailScreen({super.key, required this.record});

  final HistoryRecord record;

  @override
  Widget build(BuildContext context) {
    final summary = record.summary;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(record.filename),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: summary == null
          ? const AnalysisDetailEmptyState()
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AnalysisFileInfoCard(
                    filename: record.filename,
                    dateTime: record.createdAt,
                    basicInfo: record.basicInfo,
                    qualityScore: record.qualityScore,
                  ),
                  const SizedBox(height: 24),
                  if (_isSuccessful(record.qualityAnalysis)) ...[
                    const AnalysisSectionTitle(
                      title: '数据质量评估',
                      icon: Icons.assessment,
                    ),
                    const SizedBox(height: 12),
                    AnalysisQualitySection(
                      qualityAnalysis: record.qualityAnalysis!,
                    ),
                    const SizedBox(height: 24),
                  ],
                  if (_isSuccessful(record.correlations)) ...[
                    const AnalysisSectionTitle(
                      title: '相关性分析',
                      icon: Icons.scatter_plot,
                    ),
                    const SizedBox(height: 12),
                    AnalysisCorrelationSection(
                      correlationAnalysis: record.correlations!,
                    ),
                    const SizedBox(height: 24),
                  ],
                  if (_isSuccessful(record.statisticalTests)) ...[
                    const AnalysisSectionTitle(
                      title: '统计检验',
                      icon: Icons.functions,
                    ),
                    const SizedBox(height: 12),
                    AnalysisStatisticalSection(
                      statisticalTests: record.statisticalTests!,
                    ),
                    const SizedBox(height: 24),
                  ],
                  if (record.basicInfo != null) ...[
                    const AnalysisSectionTitle(
                      title: '数据集信息',
                      icon: Icons.info_outline,
                    ),
                    const SizedBox(height: 12),
                    AnalysisBasicInfoSection(basicInfo: record.basicInfo!),
                    const SizedBox(height: 24),
                  ],
                  if (record.preview != null) ...[
                    const AnalysisSectionTitle(
                      title: '数据预览',
                      icon: Icons.table_chart,
                    ),
                    const SizedBox(height: 12),
                    AnalysisDataPreviewSection(preview: record.preview),
                  ],
                ],
              ),
            ),
    );
  }

  bool _isSuccessful(Map<String, dynamic>? section) {
    return section != null && section['success'] == true;
  }
}
