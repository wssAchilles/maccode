library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../models/job_record.dart';
import 'data_analysis_view_model.dart';
import 'job_view_model.dart';

const _defaultWorkflowErrorDuration = Duration(seconds: 4);

class DataAnalysisWorkflowCoordinator {
  const DataAnalysisWorkflowCoordinator({
    required DataAnalysisViewModel viewModel,
    required JobViewModel analysisJobsViewModel,
    required Future<void> Function() refreshSharedProjection,
    required Future<void> Function(JobRecord job) openJob,
    required void Function({Duration duration}) showError,
    required void Function(String message) showSuccess,
    required void Function() focusAnalysisResult,
    required String Function(String action) datasetFeedbackMessage,
    required bool Function() isMounted,
  }) : _viewModel = viewModel,
       _analysisJobsViewModel = analysisJobsViewModel,
       _refreshSharedProjection = refreshSharedProjection,
       _openJob = openJob,
       _showError = showError,
       _showSuccess = showSuccess,
       _focusAnalysisResult = focusAnalysisResult,
       _datasetFeedbackMessage = datasetFeedbackMessage,
       _isMounted = isMounted;

  final DataAnalysisViewModel _viewModel;
  final JobViewModel _analysisJobsViewModel;
  final Future<void> Function() _refreshSharedProjection;
  final Future<void> Function(JobRecord job) _openJob;
  final void Function({Duration duration}) _showError;
  final void Function(String message) _showSuccess;
  final void Function() _focusAnalysisResult;
  final String Function(String action) _datasetFeedbackMessage;
  final bool Function() _isMounted;

  Future<void> pickFile() async {
    await _viewModel.pickFile();
    if (!_isMounted()) {
      return;
    }
    _showError(duration: _defaultWorkflowErrorDuration);
  }

  Future<void> startAnalysis({
    required User? currentUser,
    required PlatformFile? pickedFile,
    required Duration errorDuration,
  }) async {
    if (currentUser == null || pickedFile == null) {
      return;
    }

    final success = await _viewModel.startAnalysis();
    if (!_isMounted()) {
      return;
    }

    if (success) {
      await _refreshSharedProjection();
      _showSuccess(_datasetFeedbackMessage('分析完成'));
      _focusAnalysisResult();
      return;
    }

    _showError(duration: errorDuration);
  }

  Future<void> submitAnalysisJob({required Duration errorDuration}) async {
    final job = await _viewModel.submitAnalysisJob();
    if (!_isMounted()) {
      return;
    }

    if (job != null) {
      await _openJob(job);
      _showSuccess(_datasetFeedbackMessage('后台分析任务已提交'));
      await _analysisJobsViewModel.loadJobs();
      await _refreshSharedProjection();
      return;
    }

    _showError(duration: errorDuration);
  }
}
