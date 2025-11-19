/// API 响应模型
library;

class ApiResponse<T> {
  final bool success;
  final T? data;
  final ApiError? error;
  final Map<String, dynamic>? metadata;

  ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.metadata,
  });

  factory ApiResponse.success(T data, {Map<String, dynamic>? metadata}) {
    return ApiResponse(
      success: true,
      data: data,
      metadata: metadata,
    );
  }

  factory ApiResponse.failure(ApiError error) {
    return ApiResponse(
      success: false,
      error: error,
    );
  }

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>)? fromJsonT,
  ) {
    if (json['success'] == true || json['error'] == null) {
      T? data;
      if (fromJsonT != null && json['data'] != null) {
        data = fromJsonT(json['data'] as Map<String, dynamic>);
      } else if (json['data'] != null) {
        data = json['data'] as T;
      }

      return ApiResponse.success(
        data as T,
        metadata: json['metadata'] as Map<String, dynamic>?,
      );
    } else {
      return ApiResponse.failure(
        ApiError.fromJson(json['error'] as Map<String, dynamic>),
      );
    }
  }

  bool get isSuccess => success && error == null;
  bool get isFailure => !success || error != null;
}

class ApiError {
  final String code;
  final String message;
  final Map<String, dynamic>? details;

  ApiError({
    required this.code,
    required this.message,
    this.details,
  });

  factory ApiError.fromJson(Map<String, dynamic> json) {
    return ApiError(
      code: json['code'] as String,
      message: json['message'] as String,
      details: json['details'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'code': code,
      'message': message,
      if (details != null) 'details': details,
    };
  }

  @override
  String toString() => 'ApiError(code: $code, message: $message)';
}

class PaginatedResponse<T> {
  final List<T> items;
  final int total;
  final int page;
  final int pageSize;
  final bool hasMore;

  PaginatedResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  }) : hasMore = (page * pageSize) < total;

  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) fromJsonT,
  ) {
    return PaginatedResponse(
      items: (json['items'] as List)
          .map((item) => fromJsonT(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      page: json['page'] as int,
      pageSize: json['pageSize'] as int,
    );
  }
}
