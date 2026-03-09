/// 数据分析页面 - Glassmorphism 设计
/// 完整功能实现
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:file_picker/file_picker.dart';
import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/job_record.dart';
import '../widgets/responsive_wrapper.dart';
import '../models/analysis_result.dart';
import '../widgets/analysis/analysis_results_section.dart';
import '../widgets/analysis/data_analysis_sliver_app_bar.dart';
import '../widgets/analysis/data_analysis_state_views.dart';
import '../widgets/analysis/data_analysis_top_section.dart';
import '../widgets/analysis/data_analysis_workbench.dart';
import '../widgets/analysis/data_analysis_operations_board.dart';
import '../widgets/common/glass_card.dart';
import '../viewmodels/data_analysis_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import 'history_audit_screen.dart';

class DataAnalysisScreen extends StatefulWidget {
  const DataAnalysisScreen({
    super.key,
    this.onOpenHistory,
    this.onSendToAiLab,
    this.viewModel,
    this.embedded = false,
  });

  final VoidCallback? onOpenHistory;
  final ValueChanged<AiLabLaunchIntent>? onSendToAiLab;
  final DataAnalysisViewModel? viewModel;
  final bool embedded;

  @override
  State<DataAnalysisScreen> createState() => _DataAnalysisScreenState();
}

class _DataAnalysisScreenState extends State<DataAnalysisScreen> {
  // 表单控制器
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  late final DataAnalysisViewModel _viewModel;
  late final JobViewModel _analysisJobsViewModel;
  late final bool _ownsViewModel;

  User? get _currentUser => _viewModel.currentUser;
  PlatformFile? get _pickedFile => _viewModel.pickedFile;
  AnalysisResult? get _analysisResult => _viewModel.analysisResult;
  String? get _latestStoragePath => _viewModel.latestStoragePath;
  bool get _isLoading => _viewModel.isLoading;
  bool get _isSubmittingAnalysisJob => _viewModel.isSubmittingAnalysisJob;
  bool get _saveToStorage => _viewModel.saveToStorage;
  String? get _errorMessage => _viewModel.errorMessage;
  String get _authMode => _viewModel.authMode;

  static const _defaultErrorDuration = Duration(seconds: 4);
  static const _analysisErrorDuration = Duration(seconds: 5);

  @override
  void initState() {
    super.initState();
    _ownsViewModel = widget.viewModel == null;
    _viewModel = widget.viewModel ?? DataAnalysisViewModel();
    _analysisJobsViewModel = JobViewModel(jobType: 'analysis', limit: 8);
    _viewModel.initialize();
    _analysisJobsViewModel.loadJobs();
  }

  @override
  void dispose() {
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    _analysisJobsViewModel.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// 使用 Google 登录
  Future<void> _signInWithGoogle() async {
    final user = await _viewModel.signInWithGoogle();
    if (!mounted) return;
    if (user == null) {
      _showViewModelError();
    }
  }

  /// 邮箱密码登录
  Future<void> _signInWithEmail() async {
    await _submitEmailAuth(
      action: ({required email, required password}) {
        return _viewModel.signInWithEmail(email: email, password: password);
      },
      successMessage: (user) => '欢迎回来, ${user.email ?? "用户"}!',
    );
  }

  /// 邮箱密码注册
  Future<void> _registerWithEmail() async {
    await _submitEmailAuth(
      action: ({required email, required password}) {
        return _viewModel.registerWithEmail(email: email, password: password);
      },
      successMessage: (user) => '注册成功！欢迎, ${user.email}!',
    );
  }

  Future<void> _submitEmailAuth({
    required Future<User?> Function({
      required String email,
      required String password,
    })
    action,
    required String Function(User user) successMessage,
  }) async {
    if (!_formKey.currentState!.validate()) return;

    final user = await action(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) return;
    if (user != null) {
      _showSuccessFeedback(successMessage(user));
      return;
    }

    _showViewModelError();
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
      _showFeedback(message: '登出失败: $e', backgroundColor: AppColors.error);
    }
  }

  /// 选择文件
  Future<void> _pickFile() async {
    await _viewModel.pickFile();
    if (!mounted) return;
    _showViewModelError();
  }

  /// 开始分析 - 核心功能
  Future<void> _startAnalysis() async {
    if (_currentUser == null || _pickedFile == null) {
      return;
    }

    final success = await _viewModel.startAnalysis();
    if (!mounted) return;

    if (success) {
      _showSuccessFeedback('分析完成！');
      return;
    }

    _showViewModelError(duration: _analysisErrorDuration);
  }

  Future<void> _submitAnalysisJob() async {
    final job = await _viewModel.submitAnalysisJob();
    if (!mounted) {
      return;
    }

    if (job != null) {
      _showSuccessFeedback('后台分析任务已提交');
      await _analysisJobsViewModel.loadJobs();
      return;
    }

    _showViewModelError(duration: _analysisErrorDuration);
  }

  void _openHistory() {
    final onOpenHistory = widget.onOpenHistory;
    if (onOpenHistory != null) {
      onOpenHistory();
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const HistoryAuditScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([_viewModel, _analysisJobsViewModel]),
      builder: (context, _) {
        final content = _isLoading
            ? DataAnalysisLoadingView(isAuthenticated: _currentUser != null)
            : CustomScrollView(
                slivers: [
                  if (!widget.embedded)
                    DataAnalysisSliverAppBar(
                      isLoggedIn: _currentUser != null,
                      onOpenHistory: _openHistory,
                      onSignOut: _signOut,
                    ),
                  SliverToBoxAdapter(
                    child: ResponsiveWrapper(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            DataAnalysisWorkbenchHeader(
                              currentUser: _currentUser,
                              pickedFile: _pickedFile,
                              analysisResult: _analysisResult,
                              saveToStorage: _saveToStorage,
                              latestStoragePath: _latestStoragePath,
                            ),
                            const SizedBox(height: 24),
                            DataAnalysisOperationsBoard(
                              currentUser: _currentUser,
                              pickedFile: _pickedFile,
                              analysisResult: _analysisResult,
                              saveToStorage: _saveToStorage,
                              latestStoragePath: _latestStoragePath,
                              jobs: _analysisJobsViewModel.jobs,
                              jobsLoading: _analysisJobsViewModel.isLoading,
                              jobErrorMessage:
                                  _analysisJobsViewModel.errorMessage,
                            ),
                            const SizedBox(height: 24),
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final stacked = constraints.maxWidth < 1120;
                                final controls = DataAnalysisTopSection(
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
                                );
                                final commandDeck = DataAnalysisCommandDeck(
                                  isAuthenticated: _currentUser != null,
                                  hasFile: _pickedFile != null,
                                  isLoading: _isLoading,
                                  isSubmittingBackgroundAnalysis:
                                      _isSubmittingAnalysisJob,
                                  saveToStorage: _saveToStorage,
                                  analysisResult: _analysisResult,
                                  onStartAnalysis: _startAnalysis,
                                  onSubmitBackgroundAnalysis:
                                      _submitAnalysisJob,
                                  onOpenHistory: _openHistory,
                                );

                                if (stacked) {
                                  return Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.stretch,
                                    children: [
                                      controls,
                                      const SizedBox(height: 20),
                                      commandDeck,
                                    ],
                                  );
                                }

                                return Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Expanded(flex: 7, child: controls),
                                    const SizedBox(width: 20),
                                    Expanded(flex: 4, child: commandDeck),
                                  ],
                                );
                              },
                            ),
                            const SizedBox(height: 24),
                            _buildAnalysisJobPanel(),
                            if (_errorMessage != null) ...[
                              const SizedBox(height: 16),
                              DataAnalysisErrorBanner(
                                message: _errorMessage!,
                                onDismiss: _viewModel.clearError,
                              ),
                            ],
                            if (_analysisResult != null) ...[
                              const SizedBox(height: 24),
                              _buildWorkflowActions(),
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
              );

        if (widget.embedded) {
          return content;
        }

        return Scaffold(backgroundColor: AppColors.background, body: content);
      },
    );
  }

  /// 结果展示部分 - 响应式布局
  Widget _buildResultsSection() {
    if (_analysisResult == null) return const SizedBox.shrink();
    return AnalysisResultsSection(result: _analysisResult!);
  }

  Widget _buildWorkflowActions() {
    return DataAnalysisWorkflowActionsCard(
      storagePath: _latestStoragePath,
      savedAsAsset: _saveToStorage,
      onOpenHistory: _openHistory,
      onCopyStoragePath: _copyStoragePath,
      onSendToTraining: widget.onSendToAiLab == null
          ? null
          : () => widget.onSendToAiLab!(
              AiLabLaunchIntent.deepLearning(_latestStoragePath!),
            ),
      onSendToRag: widget.onSendToAiLab == null
          ? null
          : () => widget.onSendToAiLab!(
              AiLabLaunchIntent.rag(_latestStoragePath!),
            ),
    );
  }

  Widget _buildAnalysisJobPanel() {
    final latestJob = _analysisJobsViewModel.jobs.isEmpty
        ? null
        : _analysisJobsViewModel.jobs.first;
    final canHydrateLatest =
        latestJob != null &&
        latestJob.status == 'succeeded' &&
        latestJob.result.containsKey('analysis_result');

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('后台分析任务中心', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '大文件和长时分析统一通过任务中心观察。同步分析继续保留，用于立即查看结果。',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (canHydrateLatest)
                OutlinedButton.icon(
                  onPressed: () => _hydrateLatestAnalysisJob(latestJob),
                  icon: const Icon(Icons.download_done_rounded),
                  label: const Text('载入最近后台结果'),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (latestJob != null) ...[
            Text(
              '最近任务: ${latestJob.displayTitle} · ${latestJob.statusMessage ?? latestJob.status}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            JobEventTimeline(
              job: latestJob,
              title: '最近分析任务轨迹',
              emptyMessage: '后台分析开始执行后，这里会显示基础剖析、质量检查和统计检验阶段。',
              onRetry: latestJob.retryable
                  ? () => _retryAnalysisJob(latestJob)
                  : null,
            ),
            const SizedBox(height: 16),
          ],
          JobActivityList(
            jobs: _analysisJobsViewModel.jobs,
            emptyMessage: '暂无后台分析任务。提交后可在这里观察上传后的分析进度。',
            compact: true,
          ),
        ],
      ),
    );
  }

  Future<void> _copyStoragePath() async {
    final storagePath = _latestStoragePath;
    if (storagePath == null || storagePath.isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: storagePath));
    if (!mounted) {
      return;
    }
    _showSuccessFeedback('Storage Path 已复制');
  }

  void _hydrateLatestAnalysisJob(JobRecord latestJob) {
    final success = _viewModel.loadAnalysisResultFromJobPayload(
      latestJob.result,
    );
    if (success) {
      _showSuccessFeedback('已载入最近后台分析结果');
      return;
    }
    _showViewModelError(duration: _analysisErrorDuration);
  }

  Future<void> _retryAnalysisJob(JobRecord job) async {
    final retried = await _analysisJobsViewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      _showSuccessFeedback('后台分析任务已重新排队');
      return;
    }
    final message = _analysisJobsViewModel.errorMessage;
    if (message != null) {
      _showFeedback(message: message, backgroundColor: AppColors.error);
    }
  }

  void _showSuccessFeedback(String message) {
    _showFeedback(message: message, backgroundColor: AppColors.success);
  }

  void _showViewModelError({Duration duration = _defaultErrorDuration}) {
    final message = _errorMessage;
    if (!mounted || message == null) {
      return;
    }

    _showFeedback(
      message: message,
      backgroundColor: AppColors.error,
      duration: duration,
    );
  }

  void _showFeedback({
    required String message,
    required Color backgroundColor,
    Duration duration = _defaultErrorDuration,
  }) {
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: backgroundColor,
        duration: duration,
      ),
    );
  }
}
