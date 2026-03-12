/// RAG 兼容入口
/// 主产品路径已经统一到 AI Lab 工作台，这里只保留旧路由兼容。
library;

import 'package:flutter/material.dart';

import '../models/ai_lab_launch_intent.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/rag_view_model.dart';
import 'ai_lab_screen.dart';

class RagScreen extends StatefulWidget {
  const RagScreen({super.key, this.viewModel});

  /// 保留参数仅用于旧调用点兼容。知识链路主路径已经迁移到 AI Lab。
  final RagViewModel? viewModel;

  @override
  State<RagScreen> createState() => _RagScreenState();
}

class _RagScreenState extends State<RagScreen> {
  late final DashboardViewModel _dashboardViewModel;

  @override
  void initState() {
    super.initState();
    _dashboardViewModel = DashboardViewModel();
  }

  @override
  void dispose() {
    _dashboardViewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AiLabScreen(
      dashboardViewModel: _dashboardViewModel,
      launchIntent: AiLabLaunchIntent.rag(
        'docs/',
        collectionName: 'default',
        sourceLabel: 'Legacy Knowledge Route',
      ),
    );
  }
}
