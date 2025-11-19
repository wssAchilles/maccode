/// API 服务层
/// 封装所有后端 API 调用
library;

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import '../models/analysis_result.dart';

class ApiService {
  // 后端 API 基础 URL
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://data-science-44398.an.r.appspot.com', // 生产环境
  );

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
    
    final response = await http.post(
      Uri.parse('$_baseUrl/api/analysis/analyze-csv'),
      headers: headers,
      body: jsonEncode({
        'storage_path': storagePath,
        'filename': filename,
      }),
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
        Uri.parse('$_baseUrl/health'),
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
}
