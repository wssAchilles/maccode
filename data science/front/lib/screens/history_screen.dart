/// 历史记录页面 - Glassmorphism 设计
/// 展示用户的分析历史列表
library;

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/app_theme.dart';
import '../services/api_service.dart';
import '../widgets/common/glass_card.dart';
import 'analysis_detail_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _historyList = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  /// 加载历史记录
  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final history = await ApiService.getUserHistory(limit: 50);
      
      setState(() {
        _historyList = history;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = '加载失败: $e';
      });
    }
  }

  /// 删除历史记录
  Future<void> _deleteRecord(String recordId, int index) async {
    // 显示确认对话框
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: const Text('确定要删除这条历史记录吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await ApiService.deleteHistoryRecord(recordId);
      
      setState(() {
        _historyList.removeAt(index);
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('已删除'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('删除失败: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          // 现代化 SliverAppBar
          SliverAppBar(
            expandedHeight: 100,
            floating: false,
            pinned: true,
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            flexibleSpace: FlexibleSpaceBar(
              title: Text('分析历史', style: AppTextStyles.h4.copyWith(color: Colors.white)),
              background: Container(
                decoration: const BoxDecoration(gradient: AppColors.primaryGradient),
              ),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh_rounded),
                onPressed: _loadHistory,
                tooltip: '刷新',
              ),
              const SizedBox(width: 8),
            ],
          ),
          // 内容
          SliverToBoxAdapter(
            child: _buildBody(),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return SizedBox(
        height: MediaQuery.of(context).size.height - 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
                ),
                child: const CircularProgressIndicator(
                  color: AppColors.primary,
                  strokeWidth: 3,
                ),
              ),
              const SizedBox(height: 20),
              Text('加载中...', style: AppTextStyles.bodyMedium),
            ],
          ),
        ),
      );
    }

    if (_errorMessage != null) {
      return SizedBox(
        height: MediaQuery.of(context).size.height - 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.errorLight,
                  borderRadius: BorderRadius.circular(AppDecorations.radiusXl),
                ),
                child: const Icon(Icons.error_outline_rounded, size: 48, color: AppColors.error),
              ),
              const SizedBox(height: 20),
              Text(
                _errorMessage!,
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _loadHistory,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('重试'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_historyList.isEmpty) {
      return SizedBox(
        height: MediaQuery.of(context).size.height - 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(AppDecorations.radius2xl),
                ),
                child: Icon(Icons.history_rounded, size: 64, color: AppColors.textMuted),
              ),
              const SizedBox(height: 24),
              Text(
                '暂无历史记录',
                style: AppTextStyles.h3.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 8),
              Text(
                '开始分析数据后，历史记录会显示在这里',
                style: AppTextStyles.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 统计信息
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
                ),
                child: Text(
                  '共 ${_historyList.length} 条记录',
                  style: AppTextStyles.labelMedium.copyWith(color: AppColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 历史列表
          ...List.generate(_historyList.length, (index) {
            final record = _historyList[index];
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _buildHistoryCard(record, index),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildHistoryCard(Map<String, dynamic> record, int index) {
    final filename = record['filename'] ?? 'Unknown';
    final qualityScore = record['quality_score'];
    final createdAt = record['created_at'];
    final recordId = record['id'];

    // 解析时间
    DateTime? dateTime;
    if (createdAt != null) {
      try {
        dateTime = DateTime.parse(createdAt);
      } catch (e) {
        // 时间解析失败
      }
    }

    // 质量分数颜色
    Color scoreColor;
    IconData scoreIcon;
    if (qualityScore != null) {
      final score = qualityScore is num ? qualityScore.toDouble() : 0.0;
      if (score >= 80) {
        scoreColor = AppColors.success;
        scoreIcon = Icons.check_circle_rounded;
      } else if (score >= 60) {
        scoreColor = AppColors.warning;
        scoreIcon = Icons.warning_rounded;
      } else {
        scoreColor = AppColors.error;
        scoreIcon = Icons.error_rounded;
      }
    } else {
      scoreColor = AppColors.textMuted;
      scoreIcon = Icons.help_outline_rounded;
    }

    return GlassCard(
      padding: const EdgeInsets.all(16),
      onTap: () => _showRecordDetail(record),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(Icons.description_rounded, size: 20, color: AppColors.primary),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  filename,
                  style: AppTextStyles.labelLarge,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (qualityScore != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: scoreColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
                    border: Border.all(color: scoreColor.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(scoreIcon, size: 14, color: scoreColor),
                      const SizedBox(width: 4),
                      Text(
                        qualityScore.toStringAsFixed(1),
                        style: AppTextStyles.labelMedium.copyWith(
                          color: scoreColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          
          const SizedBox(height: 12),
          
          // 时间行
          Row(
            children: [
              Icon(Icons.access_time_rounded, size: 14, color: AppColors.textMuted),
              const SizedBox(width: 6),
              Text(
                dateTime != null
                    ? DateFormat('yyyy-MM-dd HH:mm').format(dateTime)
                    : '未知时间',
                style: AppTextStyles.bodySmall,
              ),
              const Spacer(),
              
              // 删除按钮
              IconButton(
                icon: const Icon(Icons.delete_outline_rounded, size: 18),
                onPressed: () => _deleteRecord(recordId, index),
                tooltip: '删除',
                style: IconButton.styleFrom(
                  foregroundColor: AppColors.error,
                  backgroundColor: AppColors.errorLight,
                  padding: const EdgeInsets.all(8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// 显示记录详情
  void _showRecordDetail(Map<String, dynamic> record) {
    // 导航到详细分析页面
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AnalysisDetailScreen(record: record),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(
                fontWeight: FontWeight.w500,
                color: Colors.grey,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
