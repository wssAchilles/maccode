/// RAG 对话页面
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../viewmodels/rag_view_model.dart';
import '../widgets/rag/rag_input_area.dart';
import '../widgets/rag/rag_message_list.dart';
import '../widgets/responsive_wrapper.dart';

class RagScreen extends StatefulWidget {
  const RagScreen({super.key, this.viewModel});

  final RagViewModel? viewModel;

  @override
  State<RagScreen> createState() => _RagScreenState();
}

class _RagScreenState extends State<RagScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  late final RagViewModel _viewModel;
  late final bool _ownsViewModel;
  int _lastMessageCount = 0;

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _viewModel = widget.viewModel ?? RagViewModel();
    _lastMessageCount = _viewModel.messages.length;
    _viewModel.addListener(_handleViewModelChanged);
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _viewModel.removeListener(_handleViewModelChanged);
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  void _handleViewModelChanged() {
    final count = _viewModel.messages.length;
    if (count == _lastMessageCount) {
      return;
    }

    _lastMessageCount = count;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom();
    });
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _viewModel.isLoading) {
      return;
    }

    _controller.clear();
    await _viewModel.sendMessage(text);
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) {
      return;
    }

    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent,
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('知识库助手 (RAG)'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        flexibleSpace: Opacity(
          opacity: 0.8,
          child: Container(
            decoration: const BoxDecoration(
              gradient: AppColors.ragGradient,
            ),
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppColors.backgroundGradient,
        ),
        child: SafeArea(
          child: ResponsiveWrapper(
            child: ListenableBuilder(
              listenable: _viewModel,
              builder: (context, _) {
                return Column(
                  children: [
                    Expanded(
                      child: RagMessageList(
                        messages: _viewModel.messages,
                        scrollController: _scrollController,
                      ),
                    ),
                    RagInputArea(
                      controller: _controller,
                      isLoading: _viewModel.isLoading,
                      onSend: _sendMessage,
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
