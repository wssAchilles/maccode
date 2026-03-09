/// 认证动作结果模型
library;

import 'package:firebase_auth/firebase_auth.dart';

import 'auth_failure.dart';

class AuthActionResult {
  const AuthActionResult._({this.user, this.failure});

  const AuthActionResult.success(User user) : this._(user: user);

  const AuthActionResult.failure(AuthFailure failure)
    : this._(failure: failure);

  final User? user;
  final AuthFailure? failure;

  bool get isSuccess => user != null;
  bool get isFailure => failure != null;
  bool get isCancelled => failure?.code == 'cancelled';
}
