/// 数据分析页面 ViewModel
/// 负责认证、文件选择、上传与分析流程的状态管理
library;

import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import '../models/analysis_result.dart';
import '../models/data_analysis_error.dart';
import '../models/job_record.dart';
import '../repositories/auth_repository.dart';
import '../repositories/data_analysis_repository.dart';
import '../services/auth_gateway.dart';
import '../services/data_analysis_gateway.dart';

class DataAnalysisViewModel extends ChangeNotifier {
  DataAnalysisViewModel({
    AuthRepository? authRepository,
    AuthGateway? authGateway,
    DataAnalysisRepository? repository,
    DataAnalysisGateway? dataGateway,
    bool Function()? isAuthenticated,
  }) : _authRepository =
           authRepository ?? GatewayAuthRepository(authGateway: authGateway),
       _repository =
           repository ??
           GatewayDataAnalysisRepository(dataGateway: dataGateway),
       _isAuthenticatedOverride = isAuthenticated;

  final AuthRepository _authRepository;
  final DataAnalysisRepository _repository;
  final bool Function()? _isAuthenticatedOverride;

  StreamSubscription<User?>? _authSubscription;
  bool _isDisposed = false;
  bool _isInitialized = false;

  User? _currentUser;
  PlatformFile? _pickedFile;
  AnalysisResult? _analysisResult;
  String? _latestStoragePath;
  bool _isLoading = false;
  bool _isSubmittingAnalysisJob = false;
  bool _saveToStorage = true;
  DataAnalysisError? _error;
  String _authMode = 'login';

  User? get currentUser => _currentUser;
  PlatformFile? get pickedFile => _pickedFile;
  AnalysisResult? get analysisResult => _analysisResult;
  String? get latestStoragePath => _latestStoragePath;
  bool get isLoading => _isLoading;
  bool get isSubmittingAnalysisJob => _isSubmittingAnalysisJob;
  bool get saveToStorage => _saveToStorage;
  DataAnalysisError? get error => _error;
  String? get errorMessage => _error?.message;
  String get authMode => _authMode;
  bool get _isAuthenticated =>
      _isAuthenticatedOverride?.call() ?? (_currentUser != null);

  void initialize() {
    if (_isDisposed || _isInitialized) {
      return;
    }

    _isInitialized = true;
    _currentUser = _authRepository.currentUser;
    _authSubscription = _authRepository.authStateChanges.listen((user) {
      _currentUser = user;
      if (user == null) {
        _pickedFile = null;
        _analysisResult = null;
        _latestStoragePath = null;
      }
      _notifySafely();
    });
    _notifySafely();
  }

  void toggleAuthMode() {
    _authMode = _authMode == 'login' ? 'register' : 'login';
    _error = null;
    _notifySafely();
  }

  void clearError() {
    _error = null;
    _notifySafely();
  }

  void clearPickedFile() {
    _pickedFile = null;
    _latestStoragePath = null;
    _notifySafely();
  }

  void setSaveToStorage(bool value) {
    _saveToStorage = value;
    _notifySafely();
  }

  Future<User?> signInWithGoogle() async {
    _setLoading(true);
    _error = null;
    _notifySafely();

    try {
      final result = await _authRepository.signInWithGoogle();
      if (result.isSuccess) {
        _currentUser = result.user;
        return result.user;
      }

      if (!result.isCancelled && result.failure != null) {
        _setAuthError('谷歌登录失败', result.failure!.message);
      }
      return null;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<User?> signInWithEmail({
    required String email,
    required String password,
  }) async {
    _setLoading(true);
    _error = null;
    _notifySafely();

    try {
      final result = await _authRepository.signInWithEmail(
        email: email,
        password: password,
      );
      if (result.isSuccess) {
        _currentUser = result.user;
        return result.user;
      }

      _setAuthError('登录失败', result.failure?.message ?? '未知错误');
      return null;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<User?> registerWithEmail({
    required String email,
    required String password,
  }) async {
    _setLoading(true);
    _error = null;
    _notifySafely();

    try {
      final result = await _authRepository.registerWithEmail(
        email: email,
        password: password,
      );
      if (result.isSuccess) {
        _currentUser = result.user;
        return result.user;
      }

      _setAuthError('注册失败', result.failure?.message ?? '未知错误');
      return null;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<void> signOut() async {
    await _authRepository.signOut();
    _currentUser = null;
    _pickedFile = null;
    _analysisResult = null;
    _latestStoragePath = null;
    _error = null;
    _notifySafely();
  }

  Future<bool> pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );

      if (result != null && result.files.isNotEmpty) {
        _pickedFile = result.files.first;
        _analysisResult = null;
        _error = null;
        _notifySafely();
        return true;
      }

      return false;
    } catch (e) {
      _setError(DataAnalysisErrorType.fileSelection, '选择文件失败: $e');
      _notifySafely();
      return false;
    }
  }

  Future<bool> startAnalysis() async {
    final file = _pickedFile;
    if (!_isAuthenticated || file == null) {
      _setError(DataAnalysisErrorType.validation, '请先登录并选择 CSV 文件');
      return false;
    }

    _setLoading(true);
    _error = null;
    _analysisResult = null;
    _latestStoragePath = null;
    _notifySafely();

    try {
      final submission = await _repository.submitCsvAnalysis(
        file: file,
        saveToStorage: _saveToStorage,
      );

      if (submission.isSuccess) {
        _analysisResult = submission.analysisResult;
        _latestStoragePath = submission.storagePath;
        return true;
      }

      _error = submission.error;
      return false;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<JobRecord?> submitAnalysisJob() async {
    final file = _pickedFile;
    if (!_isAuthenticated || file == null) {
      _setError(DataAnalysisErrorType.validation, '请先登录并选择 CSV 文件');
      _notifySafely();
      return null;
    }

    _isSubmittingAnalysisJob = true;
    _error = null;
    _notifySafely();

    try {
      final submission = await _repository.submitCsvAnalysisJob(
        file: file,
        saveToStorage: _saveToStorage,
      );
      if (submission.isSuccess) {
        _latestStoragePath = submission.storagePath;
        return submission.job;
      }

      _error = submission.error;
      return null;
    } finally {
      _isSubmittingAnalysisJob = false;
      _notifySafely();
    }
  }

  bool loadAnalysisResultFromJobPayload(Map<String, dynamic> payload) {
    final rawResult = payload['analysis_result'];
    if (rawResult is! Map) {
      _setError(DataAnalysisErrorType.analysis, '后台分析任务结果格式无效');
      _notifySafely();
      return false;
    }

    try {
      _analysisResult = AnalysisResult.fromJson(
        Map<String, dynamic>.from(rawResult),
      );
      final storagePath = payload['storage_path'];
      if (storagePath is String && storagePath.isNotEmpty) {
        _latestStoragePath = storagePath;
      }
      final retained = payload['storage_retained'];
      if (retained is bool) {
        _saveToStorage = retained;
      }
      _error = null;
      _notifySafely();
      return true;
    } catch (e) {
      _setError(DataAnalysisErrorType.analysis, '后台分析结果解析失败: $e');
      _notifySafely();
      return false;
    }
  }

  void loadAnalysisSnapshot({
    required AnalysisResult result,
    String? storagePath,
    String? filename,
    bool saveToStorage = false,
  }) {
    _analysisResult = result;
    _latestStoragePath = storagePath;
    _saveToStorage =
        saveToStorage || (storagePath != null && storagePath.isNotEmpty);
    if (filename != null && filename.isNotEmpty) {
      _pickedFile = PlatformFile(name: filename, size: 0);
    }
    _error = null;
    _notifySafely();
  }

  void _setLoading(bool value) {
    _isLoading = value;
  }

  @visibleForTesting
  void setPickedFileForTesting(PlatformFile? file) {
    _pickedFile = file;
  }

  void _setError(DataAnalysisErrorType type, String message) {
    _error = DataAnalysisError(type: type, message: message);
  }

  void _setAuthError(String prefix, String message) {
    _setError(DataAnalysisErrorType.auth, '$prefix: $message');
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _authSubscription?.cancel();
    _authSubscription = null;
    super.dispose();
  }
}
