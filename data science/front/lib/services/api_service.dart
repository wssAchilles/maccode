/// API 服务层
/// 封装所有后端 API 调用
library;

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import '../models/analysis_result.dart';
import '../models/optimization_result.dart';
import '../config/constants.dart';

class ApiService {
  // 后端 API 基础 URL - 使用 AppConstants 中的配置
  static String get _baseUrl => AppConstants.apiBaseUrl;

  /// 获取认证请求头
  static Future<Map<String, String>> _getAuthHeaders() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw Exception('User not authenticated');
    }

    // 获取 Firebase ID Token
    final token = await user.getIdToken();

    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  /// 验证 Token
  static Future<Map<String, dynamic>> verifyToken() async {
    final headers = await _getAuthHeaders();
    final response = await http.post(
      Uri.parse('$_baseUrl/api/auth/verify'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Token verification failed: ${response.body}');
    }
  }

  /// 获取用户资料
  static Future<Map<String, dynamic>> getUserProfile() async {
    final headers = await _getAuthHeaders();
    final response = await http.get(
      Uri.parse('$_baseUrl/api/auth/profile'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get profile: ${response.body}');
    }
  }

  /// 获取文件上传 URL
  static Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) async {
    final headers = await _getAuthHeaders();
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/data/upload-url'),
      headers: headers,
      body: jsonEncode({
        'fileName': fileName,
        'contentType': contentType,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get upload URL: ${response.body}');
    }
  }

  /// 直接上传文件到 GCS
  static Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  }) async {
    final response = await http.put(
      Uri.parse(uploadUrl),
      headers: {
        'Content-Type': contentType,
      },
      body: fileData,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to upload to GCS: ${response.statusCode} ${response.body}');
    }
  }

  /// 分析 CSV 文件
  static Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
  }) async {
    final headers = await _getAuthHeaders();
    
    final response = await http
        .post(
          Uri.parse('$_baseUrl/api/analysis/analyze-csv'),
          headers: headers,
          body: jsonEncode({
            'storage_path': storagePath,
            'filename': filename,
          }),
        )
        .timeout(
          const Duration(minutes: 3), // 大文件分析可能需要更长时间
          onTimeout: () {
            throw Exception('分析请求超时，请稍后重试或尝试较小的文件');
          },
        );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Analysis failed');
      }
      
      // 解析为强类型模型
      return AnalysisResult.fromJson(data['analysis_result']);
    } else {
      throw Exception('Analysis failed: ${response.body}');
    }
  }

  /// 获取用户文件列表
  static Future<List<String>> listUserFiles() async {
    final headers = await _getAuthHeaders();
    final response = await http.get(
      Uri.parse('$_baseUrl/api/data/list'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return List<String>.from(data['files']);
    } else {
      throw Exception('Failed to list files: ${response.body}');
    }
  }

  /// 获取文件下载链接
  static Future<String> getDownloadUrl(String filePath) async {
    final headers = await _getAuthHeaders();
    final encodedPath = Uri.encodeComponent(filePath);
    
    final response = await http.get(
      Uri.parse('$_baseUrl/api/data/download/$encodedPath'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['downloadUrl'];
    } else {
      throw Exception('Failed to get download URL: ${response.body}');
    }
  }

  /// 健康检查
  static Future<bool> checkHealth() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/health'),
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// 获取用户历史记录
  static Future<List<Map<String, dynamic>>> getUserHistory({int limit = 20}) async {
    final headers = await _getAuthHeaders();
    
    final response = await http.get(
      Uri.parse('$_baseUrl/api/history?limit=$limit'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Failed to get history');
      }
      
      return List<Map<String, dynamic>>.from(data['history']);
    } else {
      throw Exception('Failed to get history: ${response.body}');
    }
  }

  /// 获取历史记录详情
  static Future<Map<String, dynamic>> getHistoryDetail(String recordId) async {
    final headers = await _getAuthHeaders();
    
    final response = await http.get(
      Uri.parse('$_baseUrl/api/history/$recordId'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Failed to get record');
      }
      
      return data['record'];
    } else if (response.statusCode == 404) {
      throw Exception('Record not found');
    } else {
      throw Exception('Failed to get record: ${response.body}');
    }
  }

  /// 删除历史记录
  static Future<void> deleteHistoryRecord(String recordId) async {
    final headers = await _getAuthHeaders();
    
    final response = await http.delete(
      Uri.parse('$_baseUrl/api/history/$recordId'),
      headers: headers,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to delete record: ${response.body}');
    }
  }

  /// 训练机器学习模型
  static Future<Map<String, dynamic>> trainModel({
    required String storagePath,
    required String problemType,
    String? targetColumn,
    String? modelName,
    int? nClusters,
  }) async {
    final headers = await _getAuthHeaders();
    
    final body = {
      'storage_path': storagePath,
      'problem_type': problemType,
      if (targetColumn != null) 'target_column': targetColumn,
      if (modelName != null) 'model_name': modelName,
      if (nClusters != null) 'n_clusters': nClusters,
    };
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/ml/train'),
      headers: headers,
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Training failed');
      }
      return data;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Training failed: ${response.body}');
    }
  }

  /// 使用模型进行预测
  static Future<Map<String, dynamic>> predict({
    required String modelPath,
    List<Map<String, dynamic>>? inputData,
    String? storagePath,
  }) async {
    final headers = await _getAuthHeaders();
    
    final body = {
      'model_path': modelPath,
      if (inputData != null) 'input_data': inputData,
      if (storagePath != null) 'storage_path': storagePath,
    };
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/ml/predict'),
      headers: headers,
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Prediction failed');
      }
      return data;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Prediction failed: ${response.body}');
    }
  }

  /// 列出用户的所有模型
  static Future<List<Map<String, dynamic>>> listModels() async {
    final headers = await _getAuthHeaders();
    
    final response = await http.get(
      Uri.parse('$_baseUrl/api/ml/models'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Failed to list models');
      }
      return List<Map<String, dynamic>>.from(data['models']);
    } else {
      throw Exception('Failed to list models: ${response.body}');
    }
  }

  /// 获取模型信息
  static Future<Map<String, dynamic>> getModelInfo(String modelPath) async {
    final headers = await _getAuthHeaders();
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/ml/model-info'),
      headers: headers,
      body: jsonEncode({'model_path': modelPath}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] != true) {
        throw Exception(data['message'] ?? 'Failed to get model info');
      }
      return data['info'];
    } else {
      throw Exception('Failed to get model info: ${response.body}');
    }
  }

  // ========================================================================
  // 能源优化 API
  // ========================================================================

  /// 执行能源优化调度
  /// 
  /// 参数:
  ///   - [initialSoc]: 初始电池电量 (0.0-1.0)，默认 0.5
  ///   - [targetDate]: 目标日期，默认为明天
  ///   - [temperatureForecast]: 24小时温度预测列表，可选
  ///   - [batteryCapacity]: 电池容量 (kWh)，可选
  ///   - [batteryPower]: 最大功率 (kW)，可选
  ///   - [batteryEfficiency]: 充放电效率，可选
  /// 
  /// 返回: OptimizationResponse 对象
  /// 
  /// 抛出异常:
  ///   - Exception: 当认证失败、参数错误或服务器错误时
  static Future<OptimizationResponse> runOptimization({
    double initialSoc = AppConstants.defaultInitialSoc,
    DateTime? targetDate,
    List<double>? temperatureForecast,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
  }) async {
    // 验证 initialSoc 范围
    if (initialSoc < AppConstants.minSoc || initialSoc > AppConstants.maxSoc) {
      throw ArgumentError(
        'initialSoc must be between ${AppConstants.minSoc} and ${AppConstants.maxSoc}',
      );
    }

    // 验证温度预测列表长度
    if (temperatureForecast != null && temperatureForecast.length != 24) {
      throw ArgumentError('temperatureForecast must contain exactly 24 values');
    }

    try {
      // 获取认证头
      final headers = await _getAuthHeaders();

      // 构建请求体
      final body = <String, dynamic>{
        'initial_soc': initialSoc,
      };

      // 添加可选参数
      if (targetDate != null) {
        body['target_date'] = _formatDate(targetDate);
      }

      if (temperatureForecast != null) {
        body['temperature_forecast'] = temperatureForecast;
      }

      if (batteryCapacity != null) {
        body['battery_capacity'] = batteryCapacity;
      }

      if (batteryPower != null) {
        body['battery_power'] = batteryPower;
      }

      if (batteryEfficiency != null) {
        body['battery_efficiency'] = batteryEfficiency;
      }

      // 发送 POST 请求
      final response = await http
          .post(
            Uri.parse('$_baseUrl/api/optimization/run'),
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(
            AppConstants.optimizationTimeout,
            onTimeout: () {
              throw Exception('优化请求超时，请稍后重试');
            },
          );

      // 解析响应
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      // 处理不同的状态码
      if (response.statusCode == 200) {
        // 成功响应
        return OptimizationResponse.fromJson(data);
      } else if (response.statusCode == 401) {
        // 认证失败
        throw Exception(
          data['message'] ?? AppConstants.authError,
        );
      } else if (response.statusCode == 400) {
        // 参数错误
        throw Exception(
          data['message'] ?? '请求参数错误',
        );
      } else if (response.statusCode == 404) {
        // 模型未找到
        throw Exception(
          data['message'] ?? '预测模型未找到，请联系管理员',
        );
      } else if (response.statusCode == 500) {
        // 服务器错误
        final error = data['error'] as String?;
        if (error != null && error.toLowerCase().contains('license')) {
          throw Exception('优化服务暂时不可用 (许可证错误)');
        }
        throw Exception(
          data['message'] ?? AppConstants.serverError,
        );
      } else {
        // 其他错误
        throw Exception(
          data['message'] ?? '优化失败: HTTP ${response.statusCode}',
        );
      }
    } on FormatException catch (e) {
      throw Exception('响应数据格式错误: ${e.message}');
    } catch (e) {
      // 重新抛出已知异常
      if (e is Exception) rethrow;
      // 未知错误
      throw Exception('优化请求失败: $e');
    }
  }

  /// 获取优化配置
  /// 
  /// 返回电池参数和电价配置
  /// 
  /// 此接口不需要认证
  static Future<Map<String, dynamic>> getOptimizationConfig() async {
    try {
      final response = await http
          .get(
            Uri.parse('$_baseUrl/api/optimization/config'),
          )
          .timeout(
            AppConstants.apiTimeout,
            onTimeout: () {
              throw Exception('请求超时');
            },
          );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        if (data['success'] != true) {
          throw Exception(data['message'] ?? 'Failed to get config');
        }
        return data;
      } else {
        throw Exception('Failed to get config: ${response.statusCode}');
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('获取配置失败: $e');
    }
  }

  /// 场景模拟 - 对比不同电池配置
  /// 
  /// 参数:
  ///   - [targetDate]: 目标日期
  ///   - [scenarios]: 场景列表，每个场景包含 name, capacity, power
  /// 
  /// 返回: 场景对比结果
  static Future<Map<String, dynamic>> simulateScenarios({
    DateTime? targetDate,
    List<Map<String, dynamic>>? scenarios,
  }) async {
    try {
      final headers = await _getAuthHeaders();

      final body = <String, dynamic>{};

      if (targetDate != null) {
        body['target_date'] = _formatDate(targetDate);
      }

      if (scenarios != null) {
        body['scenarios'] = scenarios;
      }

      final response = await http
          .post(
            Uri.parse('$_baseUrl/api/optimization/simulate'),
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(
            AppConstants.optimizationTimeout,
            onTimeout: () {
              throw Exception('模拟请求超时');
            },
          );

      final data = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) {
        if (data['success'] != true) {
          throw Exception(data['message'] ?? 'Simulation failed');
        }
        return data;
      } else if (response.statusCode == 401) {
        throw Exception(data['message'] ?? AppConstants.authError);
      } else {
        throw Exception(data['message'] ?? '场景模拟失败');
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('场景模拟失败: $e');
    }
  }

  /// 格式化日期为 YYYY-MM-DD
  static String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }
}
