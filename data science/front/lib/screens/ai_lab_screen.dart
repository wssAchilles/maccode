/// AI Lab 工作台
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/deep_learning_config_state.dart';
import '../models/job_record.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../viewmodels/rag_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/deep_learning/deep_learning_config_panel.dart';
import '../widgets/deep_learning/deep_learning_terminal_panel.dart';
import '../widgets/operations/ai_lab_operations_board.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/operations/lab_split_panel.dart';
import '../widgets/rag/rag_input_area.dart';
import '../widgets/rag/rag_message_list.dart';
import '../widgets/responsive_wrapper.dart';

class AiLabScreen extends StatefulWidget {
  const AiLabScreen({
    super.key,
    required this.dashboardViewModel,
    this.launchIntent,
    this.onLaunchIntentHandled,
    this.embedded = false,
  });

  final DashboardViewModel dashboardViewModel;
  final AiLabLaunchIntent? launchIntent;
  final VoidCallback? onLaunchIntentHandled;
  final bool embedded;

  @override
  State<AiLabScreen> createState() => _AiLabScreenState();
}

enum _AiLabTab { deepLearning, rag }

class _AiLabScreenState extends State<AiLabScreen> {
  final _trainingStorageController = TextEditingController(
    text: 'demo_data.csv',
  );
  final _trainingTargetController = TextEditingController(text: 'Load');
  final _ragStorageController = TextEditingController(text: 'docs/');
  final _ragCollectionController = TextEditingController(text: 'default');
  final _ragQuestionController = TextEditingController();
  final _ragScrollController = ScrollController();

  late final JobViewModel _trainingJobsViewModel;
  late final JobViewModel _ragJobsViewModel;
  late final RagViewModel _ragViewModel;

  DeepLearningConfigState _config = const DeepLearningConfigState.initial();
  _AiLabTab _currentTab = _AiLabTab.deepLearning;
  bool _resetCollection = false;

  @override
  void initState() {
    super.initState();
    widget.dashboardViewModel.initialize();
    _trainingJobsViewModel = JobViewModel(jobType: 'ml_train', limit: 8);
    _ragJobsViewModel = JobViewModel(jobType: 'rag_ingest', limit: 8);
    _ragViewModel = RagViewModel();
    _applyLaunchIntent(widget.launchIntent);
    _trainingJobsViewModel.loadJobs();
    _ragJobsViewModel.loadJobs();
  }

  @override
  void didUpdateWidget(covariant AiLabScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.launchIntent != oldWidget.launchIntent) {
      _applyLaunchIntent(widget.launchIntent);
    }
  }

  @override
  void dispose() {
    _trainingStorageController.dispose();
    _trainingTargetController.dispose();
    _ragStorageController.dispose();
    _ragCollectionController.dispose();
    _ragQuestionController.dispose();
    _ragScrollController.dispose();
    _trainingJobsViewModel.dispose();
    _ragJobsViewModel.dispose();
    _ragViewModel.dispose();
    super.dispose();
  }

  Future<void> _submitTrainingJob() async {
    final job = await _trainingJobsViewModel.submitMlTrainJob(
      storagePath: _trainingStorageController.text.trim(),
      modelType: _config.modelTypeValue,
      epochs: _config.epochs,
      batchSize: _config.batchSize,
      windowSize: _config.windowSize,
      targetColumn: _trainingTargetController.text.trim(),
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('训练任务已提交: ${job.jobId.substring(0, 8)}'),
          backgroundColor: AppColors.success,
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }

    final message = _trainingJobsViewModel.errorMessage;
    if (message != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: AppColors.error),
      );
    }
  }

  Future<void> _submitRagIngestJob() async {
    final job = await _ragJobsViewModel.submitRagIngestJob(
      storagePath: _ragStorageController.text.trim(),
      collectionName: _ragCollectionController.text.trim(),
      reset: _resetCollection,
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('知识库构建任务已提交: ${job.jobId.substring(0, 8)}'),
          backgroundColor: AppColors.success,
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }

    final message = _ragJobsViewModel.errorMessage;
    if (message != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: AppColors.error),
      );
    }
  }

  Future<void> _sendRagQuestion() async {
    final text = _ragQuestionController.text.trim();
    if (text.isEmpty || _ragViewModel.isLoading) {
      return;
    }
    _ragQuestionController.clear();
    await _ragViewModel.sendMessage(text);
    if (!mounted || !_ragScrollController.hasClients) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_ragScrollController.hasClients) {
        _ragScrollController.animateTo(
          _ragScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        widget.dashboardViewModel,
        _trainingJobsViewModel,
        _ragJobsViewModel,
        _ragViewModel,
      ]),
      builder: (context, _) {
        final summary = widget.dashboardViewModel.summary;
        final tabSwitcher = _buildTabSwitcher();
        final content = ResponsiveWrapper(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.embedded) ...[
                  _buildEmbeddedHeader(tabSwitcher),
                  const SizedBox(height: 20),
                ],
                AiLabOperationsBoard(
                  summary: summary,
                  trainingJobs: _trainingJobsViewModel.jobs,
                  ragJobs: _ragJobsViewModel.jobs,
                  currentTab: _currentTab.name,
                  launchIntent: widget.launchIntent,
                  trainingStoragePath: _trainingStorageController.text.trim(),
                  ragStoragePath: _ragStorageController.text.trim(),
                  onSelectDeepLearning: () {
                    setState(() {
                      _currentTab = _AiLabTab.deepLearning;
                    });
                  },
                  onSelectRag: () {
                    setState(() {
                      _currentTab = _AiLabTab.rag;
                    });
                  },
                  onRefresh: () {
                    widget.dashboardViewModel.loadSummary();
                    _trainingJobsViewModel.loadJobs();
                    _ragJobsViewModel.loadJobs();
                  },
                ),
                const SizedBox(height: 20),
                if (_currentTab == _AiLabTab.deepLearning)
                  _buildDeepLearningTab(summary)
                else
                  _buildRagTab(summary),
              ],
            ),
          ),
        );

        if (widget.embedded) {
          return content;
        }

        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: AppBar(
            title: const Text('AI Lab'),
            backgroundColor: AppColors.surface,
            surfaceTintColor: Colors.transparent,
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 16),
                child: tabSwitcher,
              ),
            ],
          ),
          body: content,
        );
      },
    );
  }

  Widget _buildTabSwitcher() {
    return SegmentedButton<_AiLabTab>(
      showSelectedIcon: false,
      segments: const [
        ButtonSegment<_AiLabTab>(
          value: _AiLabTab.deepLearning,
          icon: Icon(Icons.model_training_rounded),
          label: Text('深度学习'),
        ),
        ButtonSegment<_AiLabTab>(
          value: _AiLabTab.rag,
          icon: Icon(Icons.auto_awesome_rounded),
          label: Text('知识助手 RAG'),
        ),
      ],
      selected: {_currentTab},
      onSelectionChanged: (selection) {
        setState(() {
          _currentTab = selection.first;
        });
      },
    );
  }

  Widget _buildEmbeddedHeader(Widget tabSwitcher) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 920;
          final titleBlock = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI Lab', style: AppTextStyles.h2),
              const SizedBox(height: 8),
              Text(
                '将深度学习训练、知识库构建和问答调试统一放到一个实验工作台中。',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                titleBlock,
                const SizedBox(height: 16),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: tabSwitcher,
                ),
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: titleBlock),
              const SizedBox(width: 16),
              tabSwitcher,
            ],
          );
        },
      ),
    );
  }

  Widget _buildDeepLearningTab(DashboardSummary? summary) {
    final focusJob = _primaryJob(
      _trainingJobsViewModel.jobs,
      _trainingJobsViewModel.activeJob,
    );
    final logs = _buildTrainingLogOutput(focusJob);
    return LabSplitPanel(
      left: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _TrainingDatasetCard(
            storageController: _trainingStorageController,
            targetController: _trainingTargetController,
          ),
          const SizedBox(height: 16),
          DeepLearningConfigPanel(
            config: _config,
            isTraining: _trainingJobsViewModel.isSubmitting,
            onModelTypeChanged: (value) {
              setState(() {
                _config = _config.copyWith(modelType: value);
              });
            },
            onEpochsChanged: (value) {
              setState(() {
                _config = _config.copyWith(epochs: value);
              });
            },
            onWindowSizeChanged: (value) {
              setState(() {
                _config = _config.copyWith(windowSize: value);
              });
            },
            onBatchSizeChanged: (value) {
              setState(() {
                _config = _config.copyWith(batchSize: value);
              });
            },
            onStartTraining: _submitTrainingJob,
          ),
        ],
      ),
      right: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DeepLearningTerminalPanel(
            isTraining: focusJob?.isRunning == true,
            logs: logs,
          ),
          if (focusJob != null) ...[
            const SizedBox(height: 16),
            JobEventTimeline(
              job: focusJob,
              title: '训练阶段轨迹',
              emptyMessage: '提交训练任务后，这里会显示数据加载、序列构造、训练与产物上传阶段。',
              onRetry: focusJob.retryable
                  ? () => _retryJob(_trainingJobsViewModel, focusJob)
                  : null,
            ),
          ],
          const SizedBox(height: 16),
          _RecentModelArtifactsCard(jobs: _trainingJobsViewModel.jobs),
          const SizedBox(height: 16),
          Text('最近训练任务', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          JobActivityList(
            jobs: _trainingJobsViewModel.jobs,
            emptyMessage: '暂无训练任务，先提交一次模型训练。',
            compact: true,
          ),
        ],
      ),
    );
  }

  Widget _buildRagTab(DashboardSummary? summary) {
    final focusJob = _primaryJob(
      _ragJobsViewModel.jobs,
      _ragJobsViewModel.activeJob,
    );
    return LabSplitPanel(
      left: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _RagIngestCard(
            storageController: _ragStorageController,
            collectionController: _ragCollectionController,
            resetCollection: _resetCollection,
            isSubmitting: _ragJobsViewModel.isSubmitting,
            onResetChanged: (value) {
              setState(() {
                _resetCollection = value;
              });
            },
            onSubmit: _submitRagIngestJob,
          ),
          const SizedBox(height: 16),
          _KnowledgeBaseSnapshotCard(jobs: _ragJobsViewModel.jobs),
          const SizedBox(height: 16),
          Text('最近知识库任务', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          JobActivityList(
            jobs: _ragJobsViewModel.jobs,
            emptyMessage: '暂无知识库构建任务。',
            compact: true,
          ),
        ],
      ),
      right: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (focusJob != null) ...[
            JobEventTimeline(
              job: focusJob,
              title: '知识库构建轨迹',
              emptyMessage: '提交知识库任务后，这里会显示文档抓取、切片和向量化阶段。',
              onRetry: focusJob.retryable
                  ? () => _retryJob(_ragJobsViewModel, focusJob)
                  : null,
            ),
            const SizedBox(height: 16),
          ],
          SizedBox(
            height: 520,
            child: GlassCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: Row(
                      children: [
                        Text('知识问答面板', style: AppTextStyles.h4),
                        const Spacer(),
                        Text(
                          _ragJobsViewModel.activeJob?.statusMessage ?? '默认知识库',
                          style: AppTextStyles.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: RagMessageList(
                      messages: _ragViewModel.messages,
                      scrollController: _ragScrollController,
                    ),
                  ),
                  RagInputArea(
                    controller: _ragQuestionController,
                    isLoading: _ragViewModel.isLoading,
                    onSend: _sendRagQuestion,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _buildTrainingLogOutput(JobRecord? focusJob) {
    if (focusJob == null) {
      return 'Ready to submit training jobs.\nProvide dataset path and target column to start.';
    }

    final buffer = StringBuffer();
    buffer.writeln(
      '[${focusJob.status.toUpperCase()}] ${focusJob.displayTitle}',
    );
    buffer.writeln('job_id: ${focusJob.jobId}');
    if (focusJob.events.isNotEmpty) {
      for (final event in focusJob.events.take(10)) {
        final timestamp = event.timestamp == null
            ? '--:--:--'
            : DateFormat('HH:mm:ss').format(event.timestamp!.toLocal());
        buffer.writeln(
          '[$timestamp] (${event.progress}%) [${event.phase}] ${event.message}',
        );
      }
    } else if (focusJob.statusMessage != null) {
      buffer.writeln('status: ${focusJob.statusMessage}');
    }
    if (focusJob.error != null) {
      buffer.writeln('error: ${focusJob.error!.message}');
    }
    final metrics = focusJob.result['metrics'];
    if (metrics is Map) {
      buffer.writeln('metrics: ${metrics.toString()}');
    }
    return buffer.toString().trim();
  }

  JobRecord? _primaryJob(List<JobRecord> jobs, JobRecord? activeJob) {
    if (activeJob != null) {
      return activeJob;
    }
    if (jobs.isEmpty) {
      return null;
    }
    return jobs.first;
  }

  Future<void> _retryJob(JobViewModel viewModel, JobRecord job) async {
    final retried = await viewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('任务已重新排队'),
          backgroundColor: AppColors.success,
        ),
      );
      widget.dashboardViewModel.loadSummary();
      return;
    }
    final message = viewModel.errorMessage;
    if (message != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: AppColors.error),
      );
    }
  }

  void _applyLaunchIntent(AiLabLaunchIntent? intent) {
    if (intent == null) {
      return;
    }

    switch (intent.target) {
      case AiLabLaunchTarget.deepLearning:
        _trainingStorageController.text = intent.storagePath;
        _currentTab = _AiLabTab.deepLearning;
        break;
      case AiLabLaunchTarget.rag:
        _ragStorageController.text = intent.storagePath;
        _currentTab = _AiLabTab.rag;
        break;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.onLaunchIntentHandled?.call();
    });
  }
}

class _TrainingDatasetCard extends StatelessWidget {
  const _TrainingDatasetCard({
    required this.storageController,
    required this.targetController,
  });

  final TextEditingController storageController;
  final TextEditingController targetController;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('训练数据与目标列', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          TextField(
            controller: storageController,
            decoration: const InputDecoration(
              labelText: 'Storage Path',
              hintText: '例如: uploads/your-data.csv',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: targetController,
            decoration: const InputDecoration(
              labelText: 'Target Column',
              hintText: '例如: Load',
            ),
          ),
        ],
      ),
    );
  }
}

class _RagIngestCard extends StatelessWidget {
  const _RagIngestCard({
    required this.storageController,
    required this.collectionController,
    required this.resetCollection,
    required this.isSubmitting,
    required this.onResetChanged,
    required this.onSubmit,
  });

  final TextEditingController storageController;
  final TextEditingController collectionController;
  final bool resetCollection;
  final bool isSubmitting;
  final ValueChanged<bool> onResetChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('知识库构建入口', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          TextField(
            controller: storageController,
            decoration: const InputDecoration(
              labelText: 'Storage Path',
              hintText: '例如: docs/ 或 uploads/manual.pdf',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: collectionController,
            decoration: const InputDecoration(
              labelText: 'Collection Name',
              hintText: '例如: default',
            ),
          ),
          const SizedBox(height: 12),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('重建集合'),
            subtitle: const Text('开启后会先清空已有同名集合。'),
            value: resetCollection,
            onChanged: isSubmitting ? null : onResetChanged,
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: isSubmitting ? null : onSubmit,
              icon: isSubmitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.cloud_upload_rounded),
              label: Text(isSubmitting ? '提交中...' : '提交知识库构建任务'),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentModelArtifactsCard extends StatelessWidget {
  const _RecentModelArtifactsCard({required this.jobs});

  final List<JobRecord> jobs;

  @override
  Widget build(BuildContext context) {
    final completedJobs = jobs
        .where(
          (job) =>
              job.status == 'succeeded' && job.result['model_path'] != null,
        )
        .take(3)
        .toList(growable: false);

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('最近训练产物', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          if (completedJobs.isEmpty)
            Text(
              '暂无已完成模型产物。提交训练任务后，这里会显示模型文件和核心指标。',
              style: AppTextStyles.bodySmall,
            )
          else
            Column(
              children: completedJobs
                  .map(
                    (job) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _ModelArtifactRow(job: job),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class _ModelArtifactRow extends StatelessWidget {
  const _ModelArtifactRow({required this.job});

  final JobRecord job;

  @override
  Widget build(BuildContext context) {
    final modelPath = job.result['model_path']?.toString() ?? 'unknown';
    final metrics = job.result['metrics'];
    final modelType = job.result['model_type']?.toString() ?? 'model';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  modelType.toUpperCase(),
                  style: AppTextStyles.labelLarge,
                ),
              ),
              Text(
                job.completedAt == null
                    ? '--'
                    : DateFormat(
                        'MM-dd HH:mm',
                      ).format(job.completedAt!.toLocal()),
                style: AppTextStyles.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 6),
          SelectableText(
            modelPath,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (metrics is Map) ...[
            const SizedBox(height: 8),
            Text(
              metrics.entries
                  .take(3)
                  .map((entry) => '${entry.key}: ${entry.value}')
                  .join('  ·  '),
              style: AppTextStyles.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

class _KnowledgeBaseSnapshotCard extends StatelessWidget {
  const _KnowledgeBaseSnapshotCard({required this.jobs});

  final List<JobRecord> jobs;

  @override
  Widget build(BuildContext context) {
    JobRecord? latest;
    for (final job in jobs) {
      if (job.status == 'succeeded' && job.result.isNotEmpty) {
        latest = job;
        break;
      }
    }

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('知识库快照', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          if (latest == null)
            Text('暂无成功的知识库构建结果。', style: AppTextStyles.bodySmall)
          else ...[
            _SnapshotRow(
              label: 'Collection',
              value: latest.result['collection']?.toString() ?? 'default',
            ),
            const SizedBox(height: 8),
            _SnapshotRow(
              label: '文档数',
              value: latest.result['count']?.toString() ?? '--',
            ),
            const SizedBox(height: 8),
            _SnapshotRow(label: '状态', value: latest.statusMessage ?? '已完成'),
            if (latest.events.isNotEmpty) ...[
              const SizedBox(height: 8),
              _SnapshotRow(label: '最近阶段', value: latest.events.last.message),
            ],
          ],
        ],
      ),
    );
  }
}

class _SnapshotRow extends StatelessWidget {
  const _SnapshotRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 92,
          child: Text(label, style: AppTextStyles.labelMedium),
        ),
        Expanded(child: Text(value, style: AppTextStyles.bodyMedium)),
      ],
    );
  }
}
