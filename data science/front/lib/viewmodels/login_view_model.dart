/// 登录页面 ViewModel
/// 收敛认证流程与页面状态，避免 UI 直接依赖 Firebase/Google SDK
library;

import 'package:flutter/foundation.dart';

import '../models/auth_failure.dart';
import '../services/auth_gateway.dart';

enum LoginSubmissionResult { signedIn, registered, failed }

class LoginViewModel extends ChangeNotifier {
  LoginViewModel({AuthGateway? authGateway})
    : _authGateway = authGateway ?? FirebaseAuthGateway();

  final AuthGateway _authGateway;

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
      await _authGateway.signInWithEmail(email: email, password: password);
      return LoginSubmissionResult.signedIn;
    } on AuthFailureException catch (failure) {
      if (!failure.failure.canAutoRegister) {
        _errorMessage = '登录失败: ${failure.message}';
        return LoginSubmissionResult.failed;
      }

      return _registerAfterFailedSignIn(
        email: email,
        password: password,
        originalFailure: failure,
      );
    } catch (e) {
      final message = e.toString();
      if (!_matchesLegacyAutoRegisterSignals(message)) {
        _errorMessage = '登录失败: $e';
        return LoginSubmissionResult.failed;
      }

      return _registerAfterFailedSignIn(
        email: email,
        password: password,
        originalFailure: null,
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
      await _authGateway.signInWithGoogle();
      return true;
    } on AuthFailureException catch (failure) {
      if (failure.code != 'cancelled') {
        _errorMessage = '谷歌登录失败: ${failure.message}';
      }
      return false;
    } catch (e) {
      _errorMessage = '谷歌登录失败: $e';
      return false;
    } finally {
      _setLoading(false);
      _notifySafely();
    }
  }

  Future<LoginSubmissionResult> _registerAfterFailedSignIn({
    required String email,
    required String password,
    required AuthFailureException? originalFailure,
  }) async {
    try {
      await _authGateway.registerWithEmail(email: email, password: password);
      return LoginSubmissionResult.registered;
    } on AuthFailureException catch (failure) {
      if (failure.code == 'email-already-in-use' && originalFailure != null) {
        _errorMessage = '登录失败: ${originalFailure.message}';
      } else {
        _errorMessage = '注册失败: ${failure.message}';
      }
      return LoginSubmissionResult.failed;
    } catch (e) {
      _errorMessage = '注册失败: $e';
      return LoginSubmissionResult.failed;
    }
  }

  bool _matchesLegacyAutoRegisterSignals(String message) {
    return message.contains('用户不存在') ||
        message.contains('user-not-found') ||
        message.contains('用户不存在或密码错误') ||
        message.contains('invalid-credential') ||
        message.contains('INVALID_LOGIN_CREDENTIALS');
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
