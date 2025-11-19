/// 数据分析页面 - 完整功能实现
library;

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../services/api_service.dart';
import '../widgets/responsive_wrapper.dart';
import '../models/analysis_result.dart';
import '../widgets/analysis/quality_dashboard.dart';
import '../widgets/analysis/correlation_matrix_view.dart';
import '../widgets/analysis/statistical_panel.dart';

class DataAnalysisScreen extends StatefulWidget {
  const DataAnalysisScreen({super.key});

  @override
  State<DataAnalysisScreen> createState() => _DataAnalysisScreenState();
}

class _DataAnalysisScreenState extends State<DataAnalysisScreen> {
  // 后端 URL - 生产环境
  static const String backendUrl = 'https://data-science-44398.an.r.appspot.com';
  
  // 状态变量
  User? _currentUser;
  PlatformFile? _pickedFile;
  AnalysisResult? _analysisResult;
  bool _isLoading = false;
  bool _saveToStorage = true;
  String? _errorMessage;
  
  // 登录模式：'login' 或 'register'
  String _authMode = 'login';
  
  // 表单控制器
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email'],
    // Web 平台需要指定客户端 ID
    // Web 平台需要指定客户端 ID
    // 注意：即使在 Android/iOS 上提供此参数通常也是安全的（会被忽略），
    // 但为了确保 Web 端的 fallback 逻辑（如果 kIsWeb 判断失效）也能正常工作，我们始终提供它。
    clientId: '355365849818-nre0eoukodlr0kvhs94utq2o5vlo1mk4.apps.googleusercontent.com',
  );

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _checkCurrentUser();
  }

  /// 检查当前登录状态
  void _checkCurrentUser() {
    final user = FirebaseAuth.instance.currentUser;
    setState(() {
      _currentUser = user;
    });
  }

  /// 使用 Google 登录
  Future<void> _signInWithGoogle() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      // Web 平台使用 Firebase Auth 的 Google Provider 直接登录
      if (kIsWeb) {
        // 创建 Google Provider
        final GoogleAuthProvider googleProvider = GoogleAuthProvider();
        
        // 添加额外的 OAuth 作用域（可选）
        googleProvider.addScope('email');
        googleProvider.setCustomParameters({
          'prompt': 'select_account',
        });

        // 使用弹出窗口登录
        final userCredential = await FirebaseAuth.instance.signInWithPopup(googleProvider);
        
        setState(() {
          _currentUser = userCredential.user;
          _isLoading = false;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('欢迎, ${_currentUser?.displayName ?? _currentUser?.email ?? "用户"}!'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        // 移动平台使用 google_sign_in 插件
        final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
        
        if (googleUser == null) {
          // 用户取消登录
          setState(() {
            _isLoading = false;
          });
          return;
        }

        // 获取认证信息
        final GoogleSignInAuthentication googleAuth = await googleUser.authentication;

        // 检查 token 是否有效
        if (googleAuth.accessToken == null || googleAuth.idToken == null) {
          setState(() {
            _isLoading = false;
          });
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Google 登录失败：无法获取认证信息 (Mobile Flow)'),
                backgroundColor: Colors.red,
              ),
            );
          }
          return;
        }

        // 创建 Firebase 凭证
        final credential = GoogleAuthProvider.credential(
          accessToken: googleAuth.accessToken,
          idToken: googleAuth.idToken,
        );

        // 登录 Firebase
        final userCredential = await FirebaseAuth.instance.signInWithCredential(credential);
        
        setState(() {
          _currentUser = userCredential.user;
          _isLoading = false;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('欢迎, ${_currentUser?.displayName ?? "用户"}!'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } on FirebaseAuthException catch (e) {
      // 处理 Firebase Auth 错误
      setState(() {
        _isLoading = false;
      });
      
      String errorMessage = 'Google 登录失败';
      if (e.code == 'popup-closed-by-user') {
        errorMessage = '登录窗口已关闭';
      } else if (e.code == 'cancelled-popup-request') {
        errorMessage = '登录请求已取消';
      } else if (e.code == 'popup-blocked') {
        errorMessage = '弹出窗口被拦截，请允许弹出窗口';
      } else if (e.code == 'network-request-failed') {
        errorMessage = '网络错误，请检查网络连接';
      }
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
          ),
        );
      }
    } on PlatformException catch (e) {
      // 处理平台特定的错误
      setState(() {
        _isLoading = false;
      });
      
      String errorMessage = 'Google 登录失败';
      if (e.code == 'sign_in_failed') {
        errorMessage = 'Google 登录失败，请重试';
      } else if (e.code == 'network_error') {
        errorMessage = '网络错误，请检查网络连接';
      }
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Google 登录失败: $e';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Google 登录失败: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// 邮箱密码登录
  Future<void> _signInWithEmail() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final userCredential = await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      setState(() {
        _currentUser = userCredential.user;
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('欢迎回来, ${_currentUser?.email ?? "用户"}!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } on FirebaseAuthException catch (e) {
      setState(() {
        _isLoading = false;
      });

      String errorMessage = '登录失败';
      if (e.code == 'user-not-found') {
        errorMessage = '该邮箱未注册';
      } else if (e.code == 'wrong-password') {
        errorMessage = '密码错误';
      } else if (e.code == 'invalid-email') {
        errorMessage = '邮箱格式不正确';
      } else if (e.code == 'user-disabled') {
        errorMessage = '该账户已被禁用';
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = '登录失败: $e';
      });
    }
  }

  /// 邮箱密码注册
  Future<void> _registerWithEmail() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final userCredential = await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      setState(() {
        _currentUser = userCredential.user;
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('注册成功！欢迎, ${_currentUser?.email}!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } on FirebaseAuthException catch (e) {
      setState(() {
        _isLoading = false;
      });

      String errorMessage = '注册失败';
      if (e.code == 'weak-password') {
        errorMessage = '密码强度不够，请使用至少6位字符';
      } else if (e.code == 'email-already-in-use') {
        errorMessage = '该邮箱已被注册';
      } else if (e.code == 'invalid-email') {
        errorMessage = '邮箱格式不正确';
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = '注册失败: $e';
      });
    }
  }

  /// 登出
  Future<void> _signOut() async {
    await FirebaseAuth.instance.signOut();
    await _googleSignIn.signOut();
    setState(() {
      _currentUser = null;
      _pickedFile = null;
      _analysisResult = null;
      _errorMessage = null;
      _emailController.clear();
      _passwordController.clear();
    });
  }

  /// 选择文件
  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true, // 重要：Web 需要加载文件数据
      );

      if (result != null && result.files.isNotEmpty) {
        setState(() {
          _pickedFile = result.files.first;
          _analysisResult = null; // 清除之前的结果
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = '选择文件失败: $e';
      });
    }
  }

  /// 开始分析 - 核心功能
  Future<void> _startAnalysis() async {
    if (_currentUser == null || _pickedFile == null) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _analysisResult = null;
    });

    try {
      // 1. 获取上传 URL
      final uploadInfo = await ApiService.getUploadUrl(
        fileName: _pickedFile!.name,
        contentType: 'text/csv',
      );
      
      final uploadUrl = uploadInfo['uploadUrl'];
      final storagePath = uploadInfo['storagePath'];
      
      // 2. 上传文件到 GCS
      await ApiService.uploadFileToGcs(
        uploadUrl: uploadUrl,
        fileData: _pickedFile!.bytes!,
        contentType: 'text/csv',
      );
      
      // 3. 调用分析 API (现在返回 AnalysisResult 对象)
      final result = await ApiService.analyzeCsv(
        storagePath: storagePath,
        filename: _pickedFile!.name,
      );

      setState(() {
        _analysisResult = result;
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('分析完成！'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = '分析失败: $e';
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('分析失败: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('数据科学即服务'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (_currentUser != null)
            IconButton(
              icon: const Icon(Icons.logout),
              onPressed: _signOut,
              tooltip: '登出',
            ),
        ],
      ),
      body: _isLoading
          ? _buildLoadingView()
          : ResponsiveWrapper(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildResponsiveTopSection(),
                    const SizedBox(height: 24),
                    _buildAnalysisButton(),
                    if (_errorMessage != null) ...[
                      const SizedBox(height: 16),
                      _buildErrorCard(),
                    ],
                    if (_analysisResult != null) ...[
                      const SizedBox(height: 24),
                      _buildResultsSection(),
                    ],
                  ],
                ),
              ),
            ),
    );
  }

  /// 响应式顶部区域 (用户信息 + 文件选择)
  Widget _buildResponsiveTopSection() {
    return LayoutBuilder(
      builder: (context, constraints) {
        // 如果宽度足够，并排显示
        if (constraints.maxWidth > 800) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _buildUserSection()),
              const SizedBox(width: 24),
              Expanded(child: _buildFileSection()),
            ],
          );
        }
        // 否则垂直排列
        return Column(
          children: [
            _buildUserSection(),
            const SizedBox(height: 24),
            _buildFileSection(),
          ],
        );
      },
    );
  }

  /// 加载视图
  Widget _buildLoadingView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            _currentUser == null ? '登录中...' : '分析中，请稍候...',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'GAE 后端可能需要几秒钟唤醒',
            style: TextStyle(color: Colors.grey),
          ),
        ],
      ),
    );
  }

  /// 用户信息部分
  Widget _buildUserSection() {
    if (_currentUser == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                const Icon(Icons.account_circle, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                Text(
                  _authMode == 'login' ? '登录以使用数据分析服务' : '注册新账户',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                
                // 邮箱输入框
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: '邮箱',
                    hintText: 'your@email.com',
                    prefixIcon: Icon(Icons.email),
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return '请输入邮箱';
                    }
                    if (!value.contains('@')) {
                      return '邮箱格式不正确';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                
                // 密码输入框
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: '密码',
                    hintText: '至少6位字符',
                    prefixIcon: Icon(Icons.lock),
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return '请输入密码';
                    }
                    if (value.length < 6) {
                      return '密码至少需要6位字符';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 24),
                
                // 登录/注册按钮
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _authMode == 'login' 
                        ? _signInWithEmail 
                        : _registerWithEmail,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: Text(
                      _authMode == 'login' ? '登录' : '注册',
                      style: const TextStyle(fontSize: 16),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                
                // 切换登录/注册
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _authMode == 'login' ? '还没有账户？' : '已有账户？',
                      style: const TextStyle(color: Colors.grey),
                    ),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          _authMode = _authMode == 'login' ? 'register' : 'login';
                          _errorMessage = null;
                        });
                      },
                      child: Text(
                        _authMode == 'login' ? '立即注册' : '返回登录',
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 8),
                const Row(
                  children: [
                    Expanded(child: Divider()),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16),
                      child: Text('或', style: TextStyle(color: Colors.grey)),
                    ),
                    Expanded(child: Divider()),
                  ],
                ),
                const SizedBox(height: 8),
                
                // Google 登录按钮
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _signInWithGoogle,
                    icon: const Icon(Icons.login),
                    label: const Text('使用 Google 登录'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Card(
      child: ListTile(
        leading: _currentUser!.photoURL != null
            ? CircleAvatar(
                backgroundImage: NetworkImage(_currentUser!.photoURL!),
              )
            : const CircleAvatar(
                child: Icon(Icons.person),
              ),
        title: Text(_currentUser!.displayName ?? _currentUser!.email ?? '用户'),
        subtitle: Text(_currentUser!.email ?? ''),
        trailing: const Icon(Icons.check_circle, color: Colors.green),
      ),
    );
  }

  /// 文件选择部分
  Widget _buildFileSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '选择 CSV 文件',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _currentUser != null ? _pickFile : null,
              icon: const Icon(Icons.file_upload),
              label: const Text('选择文件'),
            ),
            if (_pickedFile != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.insert_drive_file, color: Colors.green),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _pickedFile!.name,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          Text(
                            '${(_pickedFile!.size / 1024).toStringAsFixed(2)} KB',
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () {
                        setState(() {
                          _pickedFile = null;
                        });
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              CheckboxListTile(
                title: const Text('保存到 Cloud Storage'),
                subtitle: const Text('将文件归档以便日后查看'),
                value: _saveToStorage,
                onChanged: (value) {
                  setState(() {
                    _saveToStorage = value ?? true;
                  });
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 分析按钮
  Widget _buildAnalysisButton() {
    final canAnalyze = _currentUser != null && _pickedFile != null && !_isLoading;

    return ElevatedButton.icon(
      onPressed: canAnalyze ? _startAnalysis : null,
      icon: const Icon(Icons.analytics),
      label: const Text('开始分析'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 16),
        textStyle: const TextStyle(fontSize: 18),
      ),
    );
  }

  /// 错误卡片
  Widget _buildErrorCard() {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            const Icon(Icons.error, color: Colors.red),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _errorMessage!,
                style: const TextStyle(color: Colors.red),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 结果展示部分 - 响应式布局
  Widget _buildResultsSection() {
    if (_analysisResult == null) return const SizedBox.shrink();

    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 800;

        if (isMobile) {
          // 移动端：垂直布局
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '分析结果',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              // 质量仪表板
              if (_analysisResult!.qualityAnalysis != null)
                QualityDashboard(qualityAnalysis: _analysisResult!.qualityAnalysis!),
              
              const SizedBox(height: 16),
              
              // 基本信息
              _buildBasicInfoCard(),
              
              const SizedBox(height: 16),
              
              // 统计检验面板
              if (_analysisResult!.statisticalTests != null)
                StatisticalPanel(statisticalResult: _analysisResult!.statisticalTests!),
              
              const SizedBox(height: 16),
              
              // 相关性矩阵视图
              if (_analysisResult!.correlations != null)
                CorrelationMatrixView(
                  correlationResult: _analysisResult!.correlations!,
                  isMobile: true,
                ),
              
              const SizedBox(height: 16),
              
              // 数据预览
              _buildPreviewCard(),
            ],
          );
        } else {
          // 桌面端：分栏布局
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '分析结果',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 左侧列 (flex: 3)
                  Expanded(
                    flex: 3,
                    child: Column(
                      children: [
                        // 质量仪表板
                        if (_analysisResult!.qualityAnalysis != null)
                          QualityDashboard(
                            qualityAnalysis: _analysisResult!.qualityAnalysis!,
                          ),
                        
                        const SizedBox(height: 16),
                        
                        // 基本信息
                        _buildBasicInfoCard(),
                      ],
                    ),
                  ),
                  
                  const SizedBox(width: 24),
                  
                  // 右侧列 (flex: 7)
                  Expanded(
                    flex: 7,
                    child: Column(
                      children: [
                        // 统计检验面板
                        if (_analysisResult!.statisticalTests != null)
                          StatisticalPanel(
                            statisticalResult: _analysisResult!.statisticalTests!,
                          ),
                        
                        const SizedBox(height: 16),
                        
                        // 相关性矩阵视图
                        if (_analysisResult!.correlations != null)
                          CorrelationMatrixView(
                            correlationResult: _analysisResult!.correlations!,
                            isMobile: false,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // 数据预览（全宽）
              _buildPreviewCard(),
            ],
          );
        }
      },
    );
  }

  /// 基本信息卡片
  Widget _buildBasicInfoCard() {
    final basicInfo = _analysisResult!.basicInfo;
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.info_outline, size: 28),
                const SizedBox(width: 8),
                const Text(
                  '基本信息',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            _buildInfoRow('行数', '${basicInfo.rows}'),
            _buildInfoRow('列数', '${basicInfo.columns}'),
            const SizedBox(height: 12),
            const Text(
              '列名与类型:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: basicInfo.columnNames
                  .map((col) => Tooltip(
                        message: '类型: ${basicInfo.columnTypes[col] ?? "unknown"}',
                        child: Chip(
                          avatar: Icon(
                            _getTypeIcon(basicInfo.columnTypes[col] ?? ''),
                            size: 16,
                          ),
                          label: Text(col),
                          backgroundColor: _getTypeColor(basicInfo.columnTypes[col] ?? ''),
                        ),
                      ))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
  
  /// 根据数据类型获取图标
  IconData _getTypeIcon(String type) {
    if (type.contains('int') || type.contains('float')) {
      return Icons.numbers;
    } else if (type.contains('object') || type.contains('string')) {
      return Icons.text_fields;
    } else if (type.contains('datetime')) {
      return Icons.calendar_today;
    } else if (type.contains('bool')) {
      return Icons.toggle_on;
    }
    return Icons.help_outline;
  }
  
  /// 根据数据类型获取颜色
  Color _getTypeColor(String type) {
    if (type.contains('int') || type.contains('float')) {
      return Colors.blue.shade50;
    } else if (type.contains('object') || type.contains('string')) {
      return Colors.green.shade50;
    } else if (type.contains('datetime')) {
      return Colors.purple.shade50;
    } else if (type.contains('bool')) {
      return Colors.orange.shade50;
    }
    return Colors.grey.shade50;
  }

  /// 数据预览卡片
  Widget _buildPreviewCard() {
    final preview = _analysisResult!.preview;
    
    if (preview.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '数据预览 (前5行)',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Divider(),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: (preview[0] as Map<String, dynamic>).keys.map((key) {
                  return DataColumn(
                    label: Text(
                      key,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  );
                }).toList(),
                rows: preview.map((row) {
                  final rowMap = row as Map<String, dynamic>;
                  return DataRow(
                    cells: rowMap.values.map((value) {
                      return DataCell(Text(value?.toString() ?? ''));
                    }).toList(),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          Text(value),
        ],
      ),
    );
  }
}
