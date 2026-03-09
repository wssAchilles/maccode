/// 能源优化仪表盘页面
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../config/app_theme.dart';
import '../models/job_record.dart';
import '../models/modeling_controls_state.dart';
import '../models/optimization_result.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/job_view_model.dart';
import '../viewmodels/modeling_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/job_event_timeline.dart';
import '../widgets/modeling/modeling_control_panel.dart';
import '../widgets/modeling/modeling_results_section.dart';
import '../widgets/responsive_wrapper.dart';

class ModelingScreen extends StatefulWidget {
  const ModelingScreen({
    super.key,
    this.viewModel,
    this.nowBuilder,
    this.embedded = false,
  });

  final ModelingViewModel? viewModel;
  final DateTime Function()? nowBuilder;
  final bool embedded;

  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}

class _ModelingScreenState extends State<ModelingScreen> {
  late final ModelingViewModel _viewModel;
  late final JobViewModel _jobViewModel;
  late final bool _ownsViewModel;
  late ModelingControlsState _controls;

  bool get _isLoading => _viewModel.isLoading;
  OptimizationResponse? get _result => _viewModel.result;
  OptimizationResponse? get _previousResult => _viewModel.previousResult;
  String? get _errorMessage => _viewModel.errorMessage;

  @override
  void initState() {
    super.initState();
    _viewModel = widget.viewModel ?? ModelingViewModel();
    _jobViewModel = JobViewModel(jobType: 'optimization', limit: 8);
    _ownsViewModel = widget.viewModel == null;
    _controls = ModelingControlsState.initial(now: _now);
    _jobViewModel.loadJobs();
  }

  DateTime get _now => (widget.nowBuilder ?? DateTime.now).call();

  @override
  void dispose() {
    _jobViewModel.dispose();
    if (_ownsViewModel) {
      _viewModel.dispose();
    }
    super.dispose();
  }

  Future<void> _runOptimization({bool saveForComparison = true}) async {
    final result = await _viewModel.runOptimization(
      initialSoc: _controls.initialSoc,
      targetDate: _controls.targetDate,
      batteryCapacity: _controls.batteryCapacity,
      batteryPower: _controls.maxPower,
      temperatureAdjust: _controls.temperatureAdjust,
      saveForComparison: saveForComparison,
    );

    if (!mounted) {
      return;
    }

    if (result == null) {
      final message = _errorMessage;
      if (message != null) {
        _showErrorSnackBar(message);
      }
      return;
    }

    if (result.isSuccess) {
      _showSuccessSnackBar(
        '优化完成！节省 ${result.optimization?.summary.savingsFormatted ?? "0"}',
      );
      return;
    }

    final message = _errorMessage;
    if (message != null) {
      _showErrorSnackBar(message);
    }
  }

  Future<void> _refreshResults() async {
    if (_isLoading || _result == null) {
      return;
    }

    await _runOptimization(saveForComparison: false);
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  void _updateControls(ModelingControlsState nextState) {
    setState(() {
      _controls = nextState;
    });
  }

  Future<void> _submitOptimizationJob() async {
    final job = await _jobViewModel.submitOptimizationJob(
      initialSoc: _controls.initialSoc,
      targetDate: _controls.targetDate,
      batteryCapacity: _controls.batteryCapacity,
      batteryPower: _controls.maxPower,
      temperatureAdjust: _controls.temperatureAdjust,
    );

    if (!mounted) {
      return;
    }

    if (job != null) {
      _showSuccessSnackBar('后台优化任务已提交');
      return;
    }

    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
    }
  }

  Future<void> _selectDate() async {
    final now = _now;
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _controls.targetDate,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: DateTime(
        now.year,
        now.month,
        now.day,
      ).add(const Duration(days: 7)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue[700]!,
              onPrimary: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );

    if (!mounted || picked == null || picked == _controls.targetDate) {
      return;
    }

    _updateControls(_controls.copyWith(targetDate: picked));
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([_viewModel, _jobViewModel]),
      builder: (context, _) {
        final content = RefreshIndicator(
          onRefresh: _refreshResults,
          child: ResponsiveWrapper(
            maxWidth: ResponsiveHelper.getMaxContentWidth(context),
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: ResponsiveHelper.getPagePadding(context),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ModelingControlPanel(
                    state: _controls,
                    isLoading: _isLoading,
                    onToggleAdvancedParams: () {
                      _updateControls(
                        _controls.copyWith(
                          showAdvancedParams: !_controls.showAdvancedParams,
                        ),
                      );
                    },
                    onScenarioChanged: (scenario) {
                      _updateControls(_controls.applyScenario(scenario));
                    },
                    onInitialSocChanged: (value) {
                      _updateControls(_controls.copyWith(initialSoc: value));
                    },
                    onBatteryCapacityChanged: (value) {
                      _updateControls(
                        _controls.copyWith(batteryCapacity: value),
                      );
                    },
                    onMaxPowerChanged: (value) {
                      _updateControls(_controls.copyWith(maxPower: value));
                    },
                    onTemperatureAdjustChanged: (value) {
                      _updateControls(
                        _controls.copyWith(temperatureAdjust: value),
                      );
                    },
                    onSelectDate: _selectDate,
                    onRunOptimization: _runOptimization,
                  ),
                  const SizedBox(height: 16),
                  _buildJobPanel(),
                  const SizedBox(height: 16),
                  _buildOperationsCard(),
                  const SizedBox(height: 16),
                  ModelingResultsSection(
                    isLoading: _isLoading,
                    errorMessage: _errorMessage,
                    result: _result,
                    previousResult: _previousResult,
                    onDismissError: _viewModel.clearError,
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        );

        if (widget.embedded) {
          return content;
        }

        return Scaffold(backgroundColor: AppColors.background, body: content);
      },
    );
  }

  Widget _buildJobPanel() {
    final latestJob = _jobViewModel.jobs.isEmpty
        ? null
        : _jobViewModel.jobs.first;
    final canHydrateLatest =
        latestJob != null &&
        latestJob.status == 'succeeded' &&
        latestJob.result.containsKey('optimization');
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
                    Text('后台优化任务', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '用于长时优化和异步监控。同步优化仍然保留，用于即时试算。',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
              ),
              FilledButton.tonalIcon(
                onPressed: _jobViewModel.isSubmitting
                    ? null
                    : _submitOptimizationJob,
                icon: _jobViewModel.isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.cloud_queue_rounded),
                label: Text(_jobViewModel.isSubmitting ? '提交中...' : '提交后台任务'),
              ),
            ],
          ),
          if (latestJob != null) ...[
            const SizedBox(height: 12),
            Text(
              '最近任务: ${latestJob.displayTitle} · ${latestJob.statusMessage ?? latestJob.status}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            if (canHydrateLatest) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: () => _hydrateLatestJobResult(latestJob),
                  icon: const Icon(Icons.download_done_rounded),
                  label: const Text('载入最近后台结果'),
                ),
              ),
            ],
            const SizedBox(height: 12),
            JobEventTimeline(
              job: latestJob,
              title: '最近后台任务轨迹',
              emptyMessage: '后台优化开始执行后，这里会显示预测、求解和结果封装阶段。',
              onRetry: latestJob.retryable ? () => _retryJob(latestJob) : null,
            ),
          ],
          const SizedBox(height: 16),
          JobActivityList(
            jobs: _jobViewModel.jobs,
            emptyMessage: '暂无后台优化任务。提交后可在这里观察排队、运行和完成状态。',
            compact: true,
          ),
        ],
      ),
    );
  }

  Widget _buildOperationsCard() {
    final result = _result;
    final summary = result?.optimization?.summary;
    final hasExportableResult = result != null && result.isSuccess;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('结果操作', style: AppTextStyles.h4),
          const SizedBox(height: 8),
          Text(
            hasExportableResult
                ? '导出当前优化结果，或复制关键节省摘要给团队协作。'
                : '先运行一次优化，再导出结果或复制摘要。',
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              FilledButton.icon(
                onPressed: hasExportableResult ? _copyResultJson : null,
                icon: const Icon(Icons.download_rounded),
                label: const Text('复制结果 JSON'),
              ),
              FilledButton.tonalIcon(
                onPressed: hasExportableResult ? _copySummaryDigest : null,
                icon: const Icon(Icons.content_copy_rounded),
                label: const Text('复制节省摘要'),
              ),
              OutlinedButton.icon(
                onPressed: _jobViewModel.loadJobs,
                icon: const Icon(Icons.sync_rounded),
                label: const Text('刷新任务状态'),
              ),
            ],
          ),
          if (summary != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Text(
                '本次优化节省 ${summary.savingsFormatted}，较原始成本下降 ${summary.savingsPercentFormatted}。',
                style: AppTextStyles.bodyMedium,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _copyResultJson() async {
    final result = _result;
    if (result == null) {
      return;
    }

    final payload = const JsonEncoder.withIndent('  ').convert(result.toJson());
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar('优化结果 JSON 已复制');
  }

  Future<void> _copySummaryDigest() async {
    final summary = _result?.optimization?.summary;
    if (summary == null) {
      return;
    }

    final digest =
        '优化节省 ${summary.savingsFormatted}，'
        '总成本从 ${summary.totalCostWithoutBattery.toStringAsFixed(2)} 元 '
        '降至 ${summary.totalCostWithBattery.toStringAsFixed(2)} 元，'
        '降幅 ${summary.savingsPercentFormatted}。';
    await Clipboard.setData(ClipboardData(text: digest));
    if (!mounted) {
      return;
    }
    _showSuccessSnackBar('节省摘要已复制');
  }

  void _hydrateLatestJobResult(JobRecord latestJob) {
    final payload = latestJob.result;
    if (payload.isEmpty) {
      _showErrorSnackBar('最近后台任务尚未生成可载入结果');
      return;
    }

    final success = _viewModel.loadResultFromJobPayload(payload);
    if (success) {
      _showSuccessSnackBar('已载入最近后台优化结果');
      return;
    }

    final message = _errorMessage;
    if (message != null) {
      _showErrorSnackBar(message);
    }
  }

  Future<void> _retryJob(JobRecord job) async {
    final retried = await _jobViewModel.retryJob(job.jobId);
    if (!mounted) {
      return;
    }
    if (retried != null) {
      _showSuccessSnackBar('后台优化任务已重新排队');
      return;
    }
    final error = _jobViewModel.errorMessage;
    if (error != null) {
      _showErrorSnackBar(error);
    }
  }
}
