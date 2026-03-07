/// 认证网关接口
/// 为 ViewModel 提供可替换的认证访问层，避免直接依赖 Firebase SDK
library;

import 'package:firebase_auth/firebase_auth.dart';

import 'auth_service.dart';

abstract class AuthGateway {
  User? get currentUser;
  Stream<User?> get authStateChanges;

  Future<UserCredential> signInWithGoogle();

  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  });

  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  });

  Future<void> signOut();
}

class FirebaseAuthGateway implements AuthGateway {
  FirebaseAuthGateway({AuthService? authService})
    : _authService = authService ?? AuthService();

  final AuthService _authService;

  @override
  User? get currentUser => _authService.currentUser;

  @override
  Stream<User?> get authStateChanges => _authService.authStateChanges;

  @override
  Future<UserCredential> signInWithGoogle() => _authService.signInWithGoogle();

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) {
    return _authService.signInWithEmailPassword(
      email: email,
      password: password,
    );
  }

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) {
    return _authService.signUpWithEmailPassword(
      email: email,
      password: password,
    );
  }

  @override
  Future<void> signOut() => _authService.signOut();
}
