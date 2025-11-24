/// 应用常量配置
library;

import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class AppConstants {
  // API 配置
  // 根据平台自动选择合适的 API 地址
  static String get apiBaseUrl {
    // 1. 优先使用环境变量（构建时指定）
    const envUrl = String.fromEnvironment('API_BASE_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }
    
    // 2. 生产环境地址（GAE 后端）
    const prodUrl = 'https://data-science-44398.an.r.appspot.com';
    
    // 3. 开发环境检测
    const bool isProduction = bool.fromEnvironment('dart.vm.product');
    
    if (isProduction) {
      // 生产环境：使用 GAE 后端
      return prodUrl;
    }
    
    // 4. 开发环境地址（本地调试）
    if (kIsWeb) {
      // Web 平台使用 localhost
      return 'http://localhost:8080';
    } else if (Platform.isAndroid) {
      // Android 模拟器使用 10.0.2.2 (主机的 localhost)
      return 'http://10.0.2.2:8080';
    } else if (Platform.isIOS) {
      // iOS 模拟器可以直接使用 localhost
      return 'http://localhost:8080';
    }
    
    // 默认返回生产环境
    return prodUrl;
  }
  
  static const String apiVersion = 'v1';
  
  // 超时配置
  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration connectTimeout = Duration(seconds: 10);
  
  // 分页配置
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;
  
  // 文件上传配置
  static const int maxFileSize = 100 * 1024 * 1024; // 100 MB
  static const List<String> allowedFileTypes = [
    'csv',
    'xlsx',
    'xls',
    'json',
    'txt',
  ];
  
  // UI 配置
  static const Duration snackBarDuration = Duration(seconds: 3);
  static const Duration loadingDebounce = Duration(milliseconds: 300);
  
  // 存储键
  static const String tokenKey = 'auth_token';
  static const String userKey = 'user_data';
  static const String themeKey = 'theme_mode';
  
  // 错误消息
  static const String networkError = '网络连接失败，请检查网络设置';
  static const String serverError = '服务器错误，请稍后重试';
  static const String authError = '认证失败，请重新登录';
  static const String unknownError = '发生未知错误';
  
  // 优化服务配置
  static const Duration optimizationTimeout = Duration(seconds: 60); // 优化计算可能需要更长时间
  static const double defaultInitialSoc = 0.5; // 默认初始电量 50%
  static const double minSoc = 0.0;
  static const double maxSoc = 1.0;
}

class Routes {
  static const String login = '/login';
  static const String home = '/';
  static const String dashboard = '/dashboard';
  static const String datasets = '/datasets';
  static const String models = '/models';
  static const String predictions = '/predictions';
  static const String profile = '/profile';
  static const String settings = '/settings';
}

class StorageKeys {
  static const String userPreferences = 'user_preferences';
  static const String cachedData = 'cached_data';
  static const String offlineQueue = 'offline_queue';
}
