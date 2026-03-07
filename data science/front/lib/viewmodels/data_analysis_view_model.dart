/// 数据分析页面 ViewModel
/// 负责认证、文件选择、上传与分析流程的状态管理
library;

import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import '../models/analysis_result.dart';
import '../models/data_analysis_error.dart';
import '../services/auth_gateway.dart';
import '../services/data_analysis_gateway.dart';

class DataAnalysisViewModel extends ChangeNotifier {
  DataAnalysisViewModel({
    AuthGateway? authGateway,
    DataAnalysisGateway? dataGateway,
    bool Function()? isAuthenticated,
  }) : _authGateway = authGateway ?? FirebaseAuthGateway(),
       _dataGateway = dataGateway ?? ApiDataAnalysisGateway(),
       _isAuthenticatedOverride = isAuthenticated;

  final AuthGateway _authGateway;
  final DataAnalysisGateway _dataGateway;
  final bool Function()? _isAuthenticatedOverride;

  StreamSubscription<User?>? _authSubscription;
  bool _isDisposed = false;

  User? _currentUser;
  PlatformFile? _pickedFile;
  AnalysisResult? _analysisResult;
  bool _isLoading = false;
  bool _saveToStorage = true;
  DataAnalysisError? _error;
  String _authMode = 'login';

  User? get currentUser => _currentUser;
  PlatformFile? get pickedFile => _pickedFile;
  AnalysisResult? get analysisResult => _analysisResult;
  bool get isLoading => _isLoading;
  bool get saveToStorage => _saveToStorage;
  DataAnalysisError? get error => _error;
  String? get errorMessage => _error?.message;
  String get authMode => _authMode;
  bool get _isAuthenticated =>
      _isAuthenticatedOverride?.call() ?? (_currentUser != null);

  void initialize() {
    _currentUser = _authGateway.currentUser;
    _authSubscription = _authGateway.authStateChanges.listen((user) {
      _currentUser = user;
      if (user == null) {
        _pickedFile = null;
        _analysisResult = null;
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
      final userCredential = await _authGateway.signInWithGoogle();
      _currentUser = userCredential.user;
      return userCredential.user;
    } catch (e) {
      _setError(DataAnalysisErrorType.auth, 'Google 登录失败: $e');
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
      final userCredential = await _authGateway.signInWithEmail(
        email: email,
        password: password,
      );
      _currentUser = userCredential.user;
      return userCredential.user;
    } catch (e) {
      _setError(DataAnalysisErrorType.auth, '登录失败: $e');
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
      final userCredential = await _authGateway.registerWithEmail(
        email: email,
        password: password,
      );
      _currentUser = userCredential.user;
      return userCredential.user;
    } catch (e) {
      _setError(DataAnalysisErrorType.auth, '注册失败: $e');
      return null;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<void> signOut() async {
    await _authGateway.signOut();
    _currentUser = null;
    _pickedFile = null;
    _analysisResult = null;
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

    final bytes = file.bytes;
    if (bytes == null) {
      _setError(DataAnalysisErrorType.validation, '文件读取失败，请重新选择文件');
      _notifySafely();
      return false;
    }

    _setLoading(true);
    _error = null;
    _analysisResult = null;
    _notifySafely();

    try {
      final uploadInfo = await _dataGateway.getUploadUrl(
        fileName: file.name,
        contentType: 'text/csv',
      );

      final uploadUrl = uploadInfo['uploadUrl'] as String?;
      final storagePath = uploadInfo['storagePath'] as String?;

      if (uploadUrl == null || storagePath == null) {
        _setError(DataAnalysisErrorType.upload, '上传信息不完整，请稍后重试');
        return false;
      }

      await _dataGateway.uploadFileToGcs(
        uploadUrl: uploadUrl,
        fileData: bytes,
        contentType: 'text/csv',
      );

      final result = await _dataGateway.analyzeCsv(
        storagePath: storagePath,
        filename: file.name,
        saveToStorage: _saveToStorage,
      );

      _analysisResult = result;
      return true;
    } catch (e) {
      _setError(DataAnalysisErrorType.analysis, '分析失败: $e');
      return false;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
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

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _authSubscription?.cancel();
    super.dispose();
  }
}
