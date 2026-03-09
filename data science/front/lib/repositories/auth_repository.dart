/// 认证仓储
/// 为 ViewModel 提供稳定的认证结果模型，避免直接依赖网关异常。
library;

import 'package:firebase_auth/firebase_auth.dart';

import '../models/auth_action_result.dart';
import '../models/auth_failure.dart';
import '../services/auth_gateway.dart';

abstract class AuthRepository {
  User? get currentUser;
  Stream<User?> get authStateChanges;

  Future<AuthActionResult> signInWithGoogle();

  Future<AuthActionResult> signInWithEmail({
    required String email,
    required String password,
  });

  Future<AuthActionResult> registerWithEmail({
    required String email,
    required String password,
  });

  Future<void> signOut();
}

class GatewayAuthRepository implements AuthRepository {
  GatewayAuthRepository({AuthGateway? authGateway})
    : _authGateway = authGateway ?? FirebaseAuthGateway();

  final AuthGateway _authGateway;

  @override
  User? get currentUser => _authGateway.currentUser;

  @override
  Stream<User?> get authStateChanges => _authGateway.authStateChanges;

  @override
  Future<AuthActionResult> signInWithGoogle() {
    return _runAuthAction(_authGateway.signInWithGoogle);
  }

  @override
  Future<AuthActionResult> signInWithEmail({
    required String email,
    required String password,
  }) {
    return _runAuthAction(
      () => _authGateway.signInWithEmail(email: email, password: password),
    );
  }

  @override
  Future<AuthActionResult> registerWithEmail({
    required String email,
    required String password,
  }) {
    return _runAuthAction(
      () => _authGateway.registerWithEmail(email: email, password: password),
    );
  }

  @override
  Future<void> signOut() => _authGateway.signOut();

  Future<AuthActionResult> _runAuthAction(
    Future<UserCredential> Function() action,
  ) async {
    try {
      final credential = await action();
      final user = credential.user;
      if (user == null) {
        return const AuthActionResult.failure(
          AuthFailure(code: 'missing-user', message: '认证成功但未返回用户信息'),
        );
      }
      return AuthActionResult.success(user);
    } on AuthFailureException catch (failure) {
      return AuthActionResult.failure(failure.failure);
    } catch (error) {
      return AuthActionResult.failure(
        AuthFailure(code: 'auth-failed', message: '认证失败: $error'),
      );
    }
  }
}
