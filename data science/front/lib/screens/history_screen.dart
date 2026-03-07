/// 历史记录页面 - Glassmorphism 设计
/// 展示用户的分析历史列表
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/history_record.dart';
import '../viewmodels/history_view_model.dart';
import '../widgets/history/history_record_card.dart';
import '../widgets/history/history_state_sections.dart';
import 'analysis_detail_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, this.viewModel});

  final HistoryViewModel? viewModel;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late final HistoryViewModel _viewModel;
  late final bool _ownsViewModel;

  List<HistoryRecord> get _historyList => _viewModel.records;
  bool get _isLoading => _viewModel.isLoading;
  String? get _errorMessage => _viewModel.errorMessage;

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _viewModel = widget.viewModel ?? HistoryViewModel();
    _viewModel.initialize();
  }

  @override
  void dispose() {
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  /// 加载历史记录
  Future<void> _loadHistory() => _viewModel.loadHistory(limit: 50);

  /// 删除历史记录
  Future<void> _deleteRecord(HistoryRecord record) async {
    if (!record.hasValidId) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('无效记录，无法删除'), backgroundColor: Colors.red),
      );
      return;
    }

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

    final success = await _viewModel.deleteRecord(record.id);
    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已删除'), backgroundColor: Colors.green),
      );
      return;
    }

    final errorMessage = _errorMessage;
    if (errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _viewModel,
      builder: (context, _) {
        return Scaffold(
          backgroundColor: AppColors.background,
          body: CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 100,
                floating: false,
                pinned: true,
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                flexibleSpace: FlexibleSpaceBar(
                  title: Text(
                    '分析历史',
                    style: AppTextStyles.h4.copyWith(color: Colors.white),
                  ),
                  background: Container(
                    decoration: const BoxDecoration(
                      gradient: AppColors.primaryGradient,
                    ),
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
              if (_isLoading)
                const SliverFillRemaining(child: HistoryLoadingState())
              else if (_errorMessage != null)
                SliverFillRemaining(
                  child: HistoryErrorState(
                    message: _errorMessage ?? '加载失败',
                    onRetry: _loadHistory,
                  ),
                )
              else if (_historyList.isEmpty)
                const SliverFillRemaining(child: HistoryEmptyState())
              else ...[
                SliverToBoxAdapter(
                  child: HistorySummaryBadge(recordCount: _historyList.length),
                ),
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate((context, index) {
                      final record = _historyList[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _buildHistoryCard(record),
                      );
                    }, childCount: _historyList.length),
                  ),
                ),
                const SliverToBoxAdapter(child: SizedBox(height: 20)),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildHistoryCard(HistoryRecord record) {
    final isDeleting = record.hasValidId && _viewModel.isDeleting(record.id);

    return HistoryRecordCard(
      record: record,
      isDeleting: isDeleting,
      onOpen: () => _showRecordDetail(record),
      onDelete: () => _deleteRecord(record),
    );
  }

  /// 显示记录详情
  void _showRecordDetail(HistoryRecord record) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AnalysisDetailScreen(record: record),
      ),
    );
  }
}
