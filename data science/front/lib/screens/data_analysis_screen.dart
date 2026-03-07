/// 数据分析页面 - Glassmorphism 设计
/// 完整功能实现
library;

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:file_picker/file_picker.dart';
import '../config/app_theme.dart';
import '../widgets/responsive_wrapper.dart';
import '../models/analysis_result.dart';
import '../widgets/analysis/analysis_results_section.dart';
import '../widgets/analysis/pro_features_section.dart';
import '../widgets/analysis/data_analysis_sliver_app_bar.dart';
import '../widgets/analysis/data_analysis_state_views.dart';
import '../widgets/analysis/data_analysis_top_section.dart';
import '../viewmodels/data_analysis_view_model.dart';
import 'history_screen.dart';

class DataAnalysisScreen extends StatefulWidget {
  const DataAnalysisScreen({super.key, this.onOpenHistory, this.viewModel});

  final VoidCallback? onOpenHistory;
  final DataAnalysisViewModel? viewModel;

  @override
  State<DataAnalysisScreen> createState() => _DataAnalysisScreenState();
}

class _DataAnalysisScreenState extends State<DataAnalysisScreen> {
  // 表单控制器
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  late final DataAnalysisViewModel _viewModel;
  late final bool _ownsViewModel;

  User? get _currentUser => _viewModel.currentUser;
  PlatformFile? get _pickedFile => _viewModel.pickedFile;
  AnalysisResult? get _analysisResult => _viewModel.analysisResult;
  bool get _isLoading => _viewModel.isLoading;
  bool get _saveToStorage => _viewModel.saveToStorage;
  String? get _errorMessage => _viewModel.errorMessage;
  String get _authMode => _viewModel.authMode;

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _viewModel = widget.viewModel ?? DataAnalysisViewModel();
    _viewModel.initialize();
  }

  @override
  void dispose() {
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// 使用 Google 登录
  Future<void> _signInWithGoogle() async {
    final user = await _viewModel.signInWithGoogle();
    if (!mounted) return;
    if (user == null && _errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorMessage!), backgroundColor: Colors.red),
      );
    }
  }

  /// 邮箱密码登录
  Future<void> _signInWithEmail() async {
    if (!_formKey.currentState!.validate()) return;

    final user = await _viewModel.signInWithEmail(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) return;
    if (user != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('欢迎回来, ${user.email ?? "用户"}!'),
          backgroundColor: Colors.green,
        ),
      );
    } else if (_errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorMessage!), backgroundColor: Colors.red),
      );
    }
  }

  /// 邮箱密码注册
  Future<void> _registerWithEmail() async {
    if (!_formKey.currentState!.validate()) return;

    final user = await _viewModel.registerWithEmail(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) return;
    if (user != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('注册成功！欢迎, ${user.email}!'),
          backgroundColor: Colors.green,
        ),
      );
    } else if (_errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorMessage!), backgroundColor: Colors.red),
      );
    }
  }

  /// 登出
  Future<void> _signOut() async {
    try {
      await _viewModel.signOut();
      if (!mounted) return;
      _emailController.clear();
      _passwordController.clear();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('登出失败: $e'), backgroundColor: Colors.red),
      );
    }
  }

  /// 选择文件
  Future<void> _pickFile() async {
    await _viewModel.pickFile();
    if (!mounted) return;
    if (_errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorMessage!), backgroundColor: Colors.red),
      );
    }
  }

  /// 开始分析 - 核心功能
  Future<void> _startAnalysis() async {
    if (_currentUser == null || _pickedFile == null) {
      return;
    }

    final success = await _viewModel.startAnalysis();
    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('分析完成！'), backgroundColor: Colors.green),
      );
    } else if (_errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_errorMessage!),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 5),
        ),
      );
    }
  }

  void _openHistory() {
    final onOpenHistory = widget.onOpenHistory;
    if (onOpenHistory != null) {
      onOpenHistory();
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const HistoryScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _viewModel,
      builder: (context, _) {
        return Scaffold(
          backgroundColor: AppColors.background,
          body: _isLoading
              ? DataAnalysisLoadingView(isAuthenticated: _currentUser != null)
              : CustomScrollView(
                  slivers: [
                    DataAnalysisSliverAppBar(
                      isLoggedIn: _currentUser != null,
                      onOpenHistory: _openHistory,
                      onSignOut: _signOut,
                    ),
                    // 内容区域
                    SliverToBoxAdapter(
                      child: ResponsiveWrapper(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              DataAnalysisTopSection(
                                currentUser: _currentUser,
                                pickedFile: _pickedFile,
                                saveToStorage: _saveToStorage,
                                formKey: _formKey,
                                emailController: _emailController,
                                passwordController: _passwordController,
                                authMode: _authMode,
                                onSignInWithEmail: _signInWithEmail,
                                onRegisterWithEmail: _registerWithEmail,
                                onToggleAuthMode: _viewModel.toggleAuthMode,
                                onGoogleSignIn: _signInWithGoogle,
                                onPickFile: _pickFile,
                                onClearFile: _viewModel.clearPickedFile,
                                onStorageChanged: _viewModel.setSaveToStorage,
                              ),
                              const SizedBox(height: 24),
                              const ProFeaturesSection(),
                              const SizedBox(height: 24),
                              _buildAnalysisButton(),
                              if (_errorMessage != null) ...[
                                const SizedBox(height: 16),
                                DataAnalysisErrorBanner(
                                  message: _errorMessage!,
                                  onDismiss: _viewModel.clearError,
                                ),
                              ],
                              if (_analysisResult != null) ...[
                                const SizedBox(height: 24),
                                _buildResultsSection(),
                              ],
                              const SizedBox(height: 32),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
        );
      },
    );
  }

  /// 分析按钮 - CTA 渐变样式
  Widget _buildAnalysisButton() {
    final canAnalyze =
        _currentUser != null && _pickedFile != null && !_isLoading;

    return DataAnalysisStartButton(
      canAnalyze: canAnalyze,
      onStart: _startAnalysis,
    );
  }

  /// 结果展示部分 - 响应式布局
  Widget _buildResultsSection() {
    if (_analysisResult == null) return const SizedBox.shrink();
    return AnalysisResultsSection(result: _analysisResult!);
  }
}
