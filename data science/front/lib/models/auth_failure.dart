/// 认证失败模型
/// 为 UI 层提供稳定的错误 code/message，而不是依赖字符串匹配
library;

class AuthFailure {
  const AuthFailure({required this.code, required this.message});

  final String code;
  final String message;

  bool get canAutoRegister {
    switch (code) {
      case 'user-not-found':
      case 'invalid-credential':
        return true;
      default:
        return false;
    }
  }
}

class AuthFailureException implements Exception {
  const AuthFailureException(this.failure);

  final AuthFailure failure;

  String get code => failure.code;
  String get message => failure.message;

  @override
  String toString() => message;
}
