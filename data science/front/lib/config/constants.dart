/// 应用常量配置
library;

class AppConstants {
  // API 配置
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );
  
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
