/// API 服务异常
library;

enum ApiServiceErrorKind {
  unauthenticated,
  timeout,
  badResponse,
  server,
  unknown,
}

class ApiServiceException implements Exception {
  const ApiServiceException(
    this.message, {
    this.statusCode,
    this.kind = ApiServiceErrorKind.unknown,
    this.body,
  });

  final String message;
  final int? statusCode;
  final ApiServiceErrorKind kind;
  final String? body;

  @override
  String toString() => message;
}
