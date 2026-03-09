/// 登录页面 ViewModel
/// 收敛认证流程与页面状态，避免 UI 直接依赖 Firebase/Google SDK
library;

import 'package:flutter/foundation.dart';

import '../models/auth_failure.dart';
import '../repositories/auth_repository.dart';
import '../services/auth_gateway.dart';

enum LoginSubmissionResult { signedIn, registered, failed }

class LoginViewModel extends ChangeNotifier {
  LoginViewModel({AuthRepository? authRepository, AuthGateway? authGateway})
    : _authRepository =
          authRepository ?? GatewayAuthRepository(authGateway: authGateway);

  final AuthRepository _authRepository;

  bool _isDisposed = false;
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  bool get isLoading => _isLoading;
  bool get obscurePassword => _obscurePassword;
  String? get errorMessage => _errorMessage;

  void togglePasswordVisibility() {
    _obscurePassword = !_obscurePassword;
    _notifySafely();
  }

  void clearError() {
    _errorMessage = null;
    _notifySafely();
  }

  Future<LoginSubmissionResult> authenticateWithEmail({
    required String email,
    required String password,
  }) async {
    _setLoading(true);
    _errorMessage = null;
    _notifySafely();

    try {
      final result = await _authRepository.signInWithEmail(
        email: email,
        password: password,
      );
      if (result.isSuccess) {
        return LoginSubmissionResult.signedIn;
      }

      final failure = result.failure;
      if (failure == null) {
        _errorMessage = '登录失败: 未知错误';
        return LoginSubmissionResult.failed;
      }

      if (!failure.canAutoRegister) {
        _errorMessage = '登录失败: ${failure.message}';
        return LoginSubmissionResult.failed;
      }

      return _registerAfterFailedSignIn(
        email: email,
        password: password,
        originalFailure: failure,
      );
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<bool> signInWithGoogle() async {
    _setLoading(true);
    _errorMessage = null;
    _notifySafely();

    try {
      final result = await _authRepository.signInWithGoogle();
      if (result.isSuccess) {
        return true;
      }

      if (!result.isCancelled && result.failure != null) {
        _errorMessage = '谷歌登录失败: ${result.failure!.message}';
      }

      return false;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<LoginSubmissionResult> _registerAfterFailedSignIn({
    required String email,
    required String password,
    required AuthFailure? originalFailure,
  }) async {
    final result = await _authRepository.registerWithEmail(
      email: email,
      password: password,
    );
    if (result.isSuccess) {
      return LoginSubmissionResult.registered;
    }

    final failure = result.failure;
    if (failure != null) {
      if (failure.code == 'email-already-in-use' && originalFailure != null) {
        _errorMessage = '登录失败: ${originalFailure.message}';
      } else {
        _errorMessage = '注册失败: ${failure.message}';
      }
    }

    return LoginSubmissionResult.failed;
  }

  void _setLoading(bool value) {
    _isLoading = value;
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    super.dispose();
  }
}
