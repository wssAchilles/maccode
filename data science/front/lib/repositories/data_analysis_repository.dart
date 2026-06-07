/// 数据分析仓储
/// 收敛上传地址获取、文件上传和分析提交流程，避免 ViewModel 直接编排网关细节。
library;

import 'package:file_picker/file_picker.dart';

import '../models/data_analysis_error.dart';
import '../models/data_analysis_job_submission_result.dart';
import '../models/data_analysis_submission_result.dart';
import '../models/analysis_job_payload.dart';
import '../models/upload_submission_result.dart';
import '../services/api_service_exception.dart';
import '../services/data_analysis_gateway.dart';

enum _SubmissionStep { getUploadUrl, uploadFile, analyze, createJob }

abstract class DataAnalysisRepository {
  Future<DataAnalysisSubmissionResult> submitCsvAnalysis({
    required PlatformFile file,
    required bool saveToStorage,
  });

  Future<DataAnalysisJobSubmissionResult> submitCsvAnalysisJob({
    required PlatformFile file,
    required bool saveToStorage,
  });
}

class GatewayDataAnalysisRepository implements DataAnalysisRepository {
  GatewayDataAnalysisRepository({DataAnalysisGateway? dataGateway})
    : _dataGateway = dataGateway ?? ApiDataAnalysisGateway();

  final DataAnalysisGateway _dataGateway;

  @override
  Future<DataAnalysisSubmissionResult> submitCsvAnalysis({
    required PlatformFile file,
    required bool saveToStorage,
  }) async {
    final bytes = file.bytes;
    if (bytes == null) {
      return const DataAnalysisSubmissionResult.failure(
        DataAnalysisError(
          type: DataAnalysisErrorType.validation,
          message: '文件读取失败，请重新选择文件',
        ),
      );
    }

    var step = _SubmissionStep.getUploadUrl;

    try {
      final upload = await _prepareUpload(
        file: file,
        bytes: bytes,
        onStep: (value) => step = value,
      );
      step = _SubmissionStep.analyze;
      final result = await _dataGateway.analyzeCsv(
        storagePath: upload.storagePath,
        filename: file.name,
        saveToStorage: saveToStorage,
      );

      return DataAnalysisSubmissionResult.success(
        result,
        storagePath: upload.storagePath,
      );
    } catch (error) {
      return DataAnalysisSubmissionResult.failure(_mapFailure(step, error));
    }
  }

  @override
  Future<DataAnalysisJobSubmissionResult> submitCsvAnalysisJob({
    required PlatformFile file,
    required bool saveToStorage,
  }) async {
    final bytes = file.bytes;
    if (bytes == null) {
      return const DataAnalysisJobSubmissionResult.failure(
        DataAnalysisError(
          type: DataAnalysisErrorType.validation,
          message: '文件读取失败，请重新选择文件',
        ),
      );
    }

    var step = _SubmissionStep.getUploadUrl;

    try {
      final upload = await _prepareUpload(
        file: file,
        bytes: bytes,
        onStep: (value) => step = value,
      );
      step = _SubmissionStep.createJob;
      final jobPayload = await _dataGateway.createAnalysisJob(
        storagePath: upload.storagePath,
        filename: file.name,
        saveToStorage: saveToStorage,
      );
      final analysisJob = AnalysisJobPayload.fromJson(jobPayload);
      return DataAnalysisJobSubmissionResult.success(
        analysisJob.job,
        storagePath: upload.storagePath,
      );
    } catch (error) {
      return DataAnalysisJobSubmissionResult.failure(_mapFailure(step, error));
    }
  }

  Future<_PreparedUpload> _prepareUpload({
    required PlatformFile file,
    required List<int> bytes,
    void Function(_SubmissionStep step)? onStep,
  }) async {
    final uploadInfo = UploadSubmissionResult.fromJson(
      await _dataGateway.getUploadUrl(
        fileName: file.name,
        contentType: 'text/csv',
      ),
    );

    onStep?.call(_SubmissionStep.uploadFile);
    await _dataGateway.uploadFileToGcs(
      uploadUrl: uploadInfo.uploadUrl,
      fileData: bytes,
      contentType: 'text/csv',
    );

    return _PreparedUpload(storagePath: uploadInfo.storagePath);
  }

  DataAnalysisError _mapFailure(_SubmissionStep step, Object error) {
    if (error is ApiServiceException) {
      if (error.kind == ApiServiceErrorKind.unauthenticated) {
        return const DataAnalysisError(
          type: DataAnalysisErrorType.auth,
          message: '登录状态已失效，请重新登录后再试',
        );
      }

      return DataAnalysisError(
        type: _errorTypeForStep(step),
        message: _messageForApiError(step, error),
      );
    }

    return DataAnalysisError(
      type: _errorTypeForStep(step),
      message: '${_errorPrefixForStep(step)}: $error',
    );
  }

  DataAnalysisErrorType _errorTypeForStep(_SubmissionStep step) {
    switch (step) {
      case _SubmissionStep.getUploadUrl:
      case _SubmissionStep.uploadFile:
        return DataAnalysisErrorType.upload;
      case _SubmissionStep.analyze:
      case _SubmissionStep.createJob:
        return DataAnalysisErrorType.analysis;
    }
  }

  String _messageForApiError(_SubmissionStep step, ApiServiceException error) {
    switch (step) {
      case _SubmissionStep.getUploadUrl:
        switch (error.kind) {
          case ApiServiceErrorKind.timeout:
            return '获取上传地址超时，请稍后重试';
          case ApiServiceErrorKind.badResponse:
            return '上传准备失败，服务返回了无效响应';
          case ApiServiceErrorKind.server:
            return '上传准备失败，请稍后重试';
          case ApiServiceErrorKind.unknown:
          case ApiServiceErrorKind.unauthenticated:
            return '获取上传地址失败，请稍后重试';
        }
      case _SubmissionStep.uploadFile:
        switch (error.kind) {
          case ApiServiceErrorKind.timeout:
            return '文件上传超时，请检查网络后重试';
          case ApiServiceErrorKind.badResponse:
            return '文件上传失败，存储服务返回了无效响应';
          case ApiServiceErrorKind.server:
            return '文件上传失败，请稍后重试';
          case ApiServiceErrorKind.unknown:
          case ApiServiceErrorKind.unauthenticated:
            return '文件上传失败，请稍后重试';
        }
      case _SubmissionStep.analyze:
        switch (error.kind) {
          case ApiServiceErrorKind.timeout:
            return error.message;
          case ApiServiceErrorKind.badResponse:
            return '分析结果格式异常，请稍后重试';
          case ApiServiceErrorKind.server:
          case ApiServiceErrorKind.unknown:
          case ApiServiceErrorKind.unauthenticated:
            return '分析失败，请稍后重试';
        }
      case _SubmissionStep.createJob:
        switch (error.kind) {
          case ApiServiceErrorKind.timeout:
            return '分析任务创建超时，请稍后重试';
          case ApiServiceErrorKind.badResponse:
            return '分析任务创建失败，服务返回了无效响应';
          case ApiServiceErrorKind.server:
          case ApiServiceErrorKind.unknown:
          case ApiServiceErrorKind.unauthenticated:
            return '分析任务创建失败，请稍后重试';
        }
    }
  }

  String _errorPrefixForStep(_SubmissionStep step) {
    switch (step) {
      case _SubmissionStep.getUploadUrl:
        return '获取上传地址失败';
      case _SubmissionStep.uploadFile:
        return '文件上传失败';
      case _SubmissionStep.analyze:
        return '分析失败';
      case _SubmissionStep.createJob:
        return '创建分析任务失败';
    }
  }
}

class _PreparedUpload {
  const _PreparedUpload({required this.storagePath});

  final String storagePath;
}
