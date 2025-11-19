/// 认证服务层
/// 管理用户登录、登出和认证状态
library;

import 'package:firebase_auth/firebase_auth.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;

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
      throw _handleAuthException(e);
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
      throw _handleAuthException(e);
    }
  }

  /// 登出
  Future<void> signOut() async {
    await _auth.signOut();
  }

  /// 发送密码重置邮件
  Future<void> sendPasswordResetEmail(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
    } on FirebaseAuthException catch (e) {
      throw _handleAuthException(e);
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
  String _handleAuthException(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return '用户不存在';
      case 'wrong-password':
        return '密码错误';
      case 'email-already-in-use':
        return '邮箱已被注册';
      case 'invalid-email':
        return '邮箱格式不正确';
      case 'weak-password':
        return '密码强度太弱';
      case 'operation-not-allowed':
        return '操作不被允许';
      case 'user-disabled':
        return '用户已被禁用';
      default:
        return '认证失败: ${e.message}';
    }
  }
}
