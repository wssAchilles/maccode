/// 认证服务层
/// 管理用户登录、登出和认证状态
library;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:google_sign_in/google_sign_in.dart';

import '../models/auth_failure.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  GoogleSignIn? _googleSignIn;

  GoogleSignIn get _nativeGoogleSignIn => _googleSignIn ??= GoogleSignIn();

  /// 获取当前用户
  User? get currentUser => _auth.currentUser;

  /// 用户认证状态流
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  /// 邮箱密码登录
  Future<UserCredential> signInWithEmailPassword({
    required String email,
    required String password,
  }) async {
    try {
      return await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    } on FirebaseAuthException catch (e) {
      throw AuthFailureException(_mapAuthException(e));
    }
  }

  /// 邮箱密码注册
  Future<UserCredential> signUpWithEmailPassword({
    required String email,
    required String password,
  }) async {
    try {
      return await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
    } on FirebaseAuthException catch (e) {
      throw AuthFailureException(_mapAuthException(e));
    }
  }

  /// 谷歌登录
  Future<UserCredential> signInWithGoogle() async {
    try {
      if (kIsWeb) {
        // Web 平台使用 Firebase Auth 内建的 OAuth 流程
        final googleProvider = GoogleAuthProvider();
        googleProvider.setCustomParameters({'prompt': 'select_account'});
        return await _auth.signInWithPopup(googleProvider);
      }

      // 移动 & 桌面平台使用 google_sign_in 插件
      final GoogleSignInAccount? googleUser = await _nativeGoogleSignIn
          .signIn();

      if (googleUser == null) {
        throw const AuthFailureException(
          AuthFailure(code: 'cancelled', message: '登录已取消'),
        );
      }

      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;

      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      return await _auth.signInWithCredential(credential);
    } on FirebaseAuthException catch (e) {
      throw AuthFailureException(_mapAuthException(e));
    } catch (e) {
      if (e is AuthFailureException) {
        rethrow;
      }
      throw AuthFailureException(
        AuthFailure(code: 'google-sign-in-failed', message: '谷歌登录失败: $e'),
      );
    }
  }

  /// 登出
  Future<void> signOut() async {
    await _auth.signOut();

    if (!kIsWeb) {
      // Web 平台不使用 GoogleSignIn 插件
      await _googleSignIn?.signOut();
    }
  }

  /// 发送密码重置邮件
  Future<void> sendPasswordResetEmail(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
    } on FirebaseAuthException catch (e) {
      throw AuthFailureException(_mapAuthException(e));
    }
  }

  /// 获取当前用户的 ID Token
  Future<String?> getIdToken() async {
    final user = currentUser;
    if (user == null) return null;
    return await user.getIdToken();
  }

  /// 刷新 Token
  Future<String?> refreshToken() async {
    final user = currentUser;
    if (user == null) return null;
    return await user.getIdToken(true); // 强制刷新
  }

  /// 处理 Firebase 认证异常
  AuthFailure _mapAuthException(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return const AuthFailure(code: 'user-not-found', message: '用户不存在');
      case 'wrong-password':
        return const AuthFailure(code: 'wrong-password', message: '密码错误');
      case 'invalid-credential':
      case 'INVALID_LOGIN_CREDENTIALS':
        // Firebase 新版本合并了 user-not-found 和 wrong-password
        return const AuthFailure(
          code: 'invalid-credential',
          message: '用户不存在或密码错误',
        );
      case 'email-already-in-use':
        return const AuthFailure(
          code: 'email-already-in-use',
          message: '邮箱已被注册',
        );
      case 'invalid-email':
        return const AuthFailure(code: 'invalid-email', message: '邮箱格式不正确');
      case 'weak-password':
        return const AuthFailure(code: 'weak-password', message: '密码强度太弱');
      case 'operation-not-allowed':
        return const AuthFailure(
          code: 'operation-not-allowed',
          message: '操作不被允许',
        );
      case 'user-disabled':
        return const AuthFailure(code: 'user-disabled', message: '用户已被禁用');
      default:
        return AuthFailure(code: 'auth-failed', message: '认证失败: ${e.message}');
    }
  }
}
