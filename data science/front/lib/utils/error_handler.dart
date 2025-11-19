/// 错误处理工具
library;

import 'package:flutter/material.dart';
import '../models/api_response.dart';
import '../config/constants.dart';

class ErrorHandler {
  /// 处理 API 错误并返回用户友好的消息
  static String getErrorMessage(dynamic error) {
    if (error is ApiError) {
      return _getApiErrorMessage(error);
    } else if (error is Exception) {
      return _getExceptionMessage(error);
    } else {
      return AppConstants.unknownError;
    }
  }

  static String _getApiErrorMessage(ApiError error) {
    switch (error.code) {
      case 'UNAUTHORIZED':
      case 'AUTHENTICATION_ERROR':
        return AppConstants.authError;
      case 'VALIDATION_ERROR':
        return error.message;
      case 'RESOURCE_NOT_FOUND':
        return '请求的资源不存在';
      case 'RATE_LIMIT_EXCEEDED':
        return '请求过于频繁，请稍后再试';
      case 'STORAGE_ERROR':
        return '存储服务错误';
      case 'INTERNAL_ERROR':
        return AppConstants.serverError;
      default:
        return error.message;
    }
  }

  static String _getExceptionMessage(Exception error) {
    final errorString = error.toString();
    
    if (errorString.contains('SocketException') ||
        errorString.contains('NetworkException')) {
      return AppConstants.networkError;
    } else if (errorString.contains('TimeoutException')) {
      return '请求超时，请重试';
    } else if (errorString.contains('FormatException')) {
      return '数据格式错误';
    } else {
      return AppConstants.unknownError;
    }
  }

  /// 显示错误提示
  static void showErrorSnackBar(BuildContext context, dynamic error) {
    final message = getErrorMessage(error);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: AppConstants.snackBarDuration,
        action: SnackBarAction(
          label: '关闭',
          textColor: Colors.white,
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }

  /// 显示成功提示
  static void showSuccessSnackBar(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
        duration: AppConstants.snackBarDuration,
      ),
    );
  }

  /// 显示错误对话框
  static Future<void> showErrorDialog(
    BuildContext context,
    dynamic error, {
    String title = '错误',
  }) async {
    final message = getErrorMessage(error);
    
    return showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }
}
