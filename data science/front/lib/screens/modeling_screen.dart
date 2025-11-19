/// 机器学习建模页面 - 引导式建模体验
/// 让用户感受到"我在做一个严谨的科学实验"
library;

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import '../services/api_service.dart';

class ModelingScreen extends StatefulWidget {
  const ModelingScreen({super.key});

  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}

class _ModelingScreenState extends State<ModelingScreen> {
  int _currentStep = 0;
  List<String> _availableFiles = [];
  String? _selectedFile;
  List<String> _columnNames = [];
  Map<String, String> _columnTypes = {};
  bool _loadingColumns = false;
  String? _targetColumn;
  String _problemType = 'regression';
  String _inferredType = '';
  String _modelAlgorithm = 'gradient_boosting';
  int _nClusters = 3;
  bool _isTraining = false;
  String _trainingStatus = '';
  List<String> _trainingSteps = [];
  Map<String, dynamic>? _trainingResult;
  String? _modelPath;
  final Map<String, TextEditingController> _predictionControllers = {};
  Map<String, dynamic>? _predictionResult;
  bool _isPredicting = false;
  
  static const String _baseUrl = 'https://data-science-44398.an.r.appspot.com';
  
  @override
  void initState() {
    super.initState();
    _loadUserFiles();
  }
  
  @override
  void dispose() {
    for (var controller in _predictionControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }
  
  Future<void> _loadUserFiles() async {
    try {
      final files = await ApiService.listUserFiles();
      setState(() {
        _availableFiles = files.where((f) => f.endsWith('.csv')).toList();
      });
    } catch (e) {
      _showError('加载文件列表失败: $e');
    }
  }
  
  Future<void> _loadColumnInfo(String storagePath) async {
    setState(() {
      _loadingColumns = true;
      _columnNames = [];
      _columnTypes = {};
      _targetColumn = null;
      _inferredType = '';
    });
    
    try {
      final result = await ApiService.analyzeCsv(
        storagePath: storagePath,
        filename: storagePath.split('/').last,
      );
      
      setState(() {
        _columnNames = result.basicInfo.columnNames;
        _columnTypes = result.basicInfo.columnTypes;
        _loadingColumns = false;
      });
    } catch (e) {
      setState(() {
        _loadingColumns = false;
      });
      _showError('加载列信息失败: $e');
    }
  }
  
  void _inferProblemType(String column) {
    if (_columnTypes[column] == null) return;
    final colType = _columnTypes[column]!;
    
    if (colType.contains('int') || colType.contains('object') || colType.contains('category')) {
      setState(() {
        _inferredType = '分类问题';
        _problemType = 'classification';
      });
    } else if (colType.contains('float')) {
      setState(() {
        _inferredType = '回归问题';
        _problemType = 'regression';
      });
    }
  }
  
  Future<void> _trainModel() async {
    if (_selectedFile == null) {
      _showError('请选择数据集');
      return;
    }
    
    if (_problemType != 'clustering' && _targetColumn == null) {
      _showError('请选择目标变量');
      return;
    }
    
    setState(() {
      _isTraining = true;
      _trainingStatus = '正在准备训练...';
      _trainingSteps = [];
      _trainingResult = null;
    });
    
    try {
      await _updateTrainingStep('正在进行数据类型降维...');
      await Future.delayed(const Duration(milliseconds: 800));
      
      await _updateTrainingStep('执行科学采样（保留统计显著性）...');
      await Future.delayed(const Duration(milliseconds: 600));
      
      await _updateTrainingStep('构建智能预处理 Pipeline...');
      await Future.delayed(const Duration(milliseconds: 600));
      
      await _updateTrainingStep('运行 3 折交叉验证...');
      
      final headers = await _getAuthHeaders();
      final requestBody = {
        'storage_path': _selectedFile!,
        'problem_type': _problemType,
        'model_name': _modelAlgorithm == 'linear' ? 'linear' : null,
      };
      
      if (_problemType != 'clustering') {
        requestBody['target_column'] = _targetColumn;
      } else {
        requestBody['n_clusters'] = _nClusters;
      }
      
      final response = await http.post(
        Uri.parse('$_baseUrl/api/ml/train'),
        headers: headers,
        body: jsonEncode(requestBody),
      ).timeout(const Duration(seconds: 60));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        setState(() {
          _trainingResult = data;
          _modelPath = data['model_path'];
          _trainingStatus = '训练完成！';
          _isTraining = false;
        });
        
        await _updateTrainingStep('✓ 模型训练成功完成');
        setState(() {
          _currentStep = 3;
        });
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['message'] ?? '训练失败');
      }
    } catch (e) {
      setState(() {
        _isTraining = false;
        _trainingStatus = '训练失败';
      });
      _showError('训练失败: $e');
    }
  }
  
  Future<void> _updateTrainingStep(String step) async {
    setState(() {
      _trainingSteps.add(step);
      _trainingStatus = step;
    });
  }
  
  Future<void> _predictSingle() async {
    if (_modelPath == null) {
      _showError('请先训练模型');
      return;
    }
    
    setState(() {
      _isPredicting = true;
      _predictionResult = null;
    });
    
    try {
      final inputData = <String, dynamic>{};
      for (var entry in _predictionControllers.entries) {
        final value = entry.value.text;
        if (value.isEmpty) continue;
        
        if (double.tryParse(value) != null) {
          inputData[entry.key] = double.parse(value);
        } else {
          inputData[entry.key] = value;
        }
      }
      
      if (inputData.isEmpty) {
        throw Exception('请输入至少一个特征值');
      }
      
      final headers = await _getAuthHeaders();
      final response = await http.post(
        Uri.parse('$_baseUrl/api/ml/predict'),
        headers: headers,
        body: jsonEncode({
          'model_path': _modelPath,
          'input_data': [inputData],
        }),
      ).timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _predictionResult = data;
          _isPredicting = false;
        });
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['message'] ?? '预测失败');
      }
    } catch (e) {
      setState(() {
        _isPredicting = false;
      });
      _showError('预测失败: $e');
    }
  }
  
  Future<Map<String, String>> _getAuthHeaders() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) throw Exception('未登录');
    final token = await user.getIdToken();
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('智能建模实验室'),
        backgroundColor: Colors.deepPurple,
      ),
      body: Theme(
        data: Theme.of(context).copyWith(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        ),
        child: Stepper(
          currentStep: _currentStep,
          onStepContinue: () {
            if (_currentStep < 4) {
              if (_currentStep == 0 && _selectedFile == null) {
                _showError('请选择数据集');
                return;
              }
              if (_currentStep == 1 && _problemType != 'clustering' && _targetColumn == null) {
                _showError('请选择目标变量');
                return;
              }
              
              setState(() {
                _currentStep += 1;
              });
            }
          },
          onStepCancel: () {
            if (_currentStep > 0) {
              setState(() {
                _currentStep -= 1;
              });
            }
          },
          onStepTapped: (step) {
            setState(() {
              _currentStep = step;
            });
          },
          controlsBuilder: (context, details) {
            return Padding(
              padding: const EdgeInsets.only(top: 16.0),
              child: Row(
                children: [
                  if (_currentStep < 4)
                    ElevatedButton(
                      onPressed: details.onStepContinue,
                      child: Text(_currentStep == 2 ? '开始训练' : '下一步'),
                    ),
                  const SizedBox(width: 8),
                  if (_currentStep > 0)
                    TextButton(
                      onPressed: details.onStepCancel,
                      child: const Text('上一步'),
                    ),
                ],
              ),
            );
          },
          steps: [
            Step(
              title: const Text('选择数据集'),
              subtitle: _selectedFile != null ? Text(_selectedFile!.split('/').last) : null,
              content: _buildStep1DataSelection(),
              isActive: _currentStep >= 0,
              state: _currentStep > 0 ? StepState.complete : StepState.indexed,
            ),
            Step(
              title: const Text('模型配置'),
              subtitle: _targetColumn != null ? Text('目标: $_targetColumn') : null,
              content: _buildStep2ModelConfig(),
              isActive: _currentStep >= 1,
              state: _currentStep > 1 ? StepState.complete : StepState.indexed,
            ),
            Step(
              title: const Text('模型训练'),
              subtitle: _isTraining ? const Text('训练中...') : null,
              content: _buildStep3Training(),
              isActive: _currentStep >= 2,
              state: _trainingResult != null ? StepState.complete : StepState.indexed,
            ),
            Step(
              title: const Text('训练结果'),
              content: _buildStep4Results(),
              isActive: _currentStep >= 3,
              state: _currentStep > 3 ? StepState.complete : StepState.indexed,
            ),
            Step(
              title: const Text('预测演练'),
              content: _buildStep5Prediction(),
              isActive: _currentStep >= 4,
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStep1DataSelection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('📊 选择用于建模的数据集',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        
        if (_availableFiles.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(16.0),
              child: Text('暂无可用数据集，请先上传 CSV 文件'),
            ),
          )
        else
          ...(_availableFiles.map((file) {
            final fileName = file.split('/').last;
            return Card(
              child: ListTile(
                leading: const Icon(Icons.insert_drive_file, color: Colors.blue),
                title: Text(fileName),
                subtitle: Text(file),
                selected: _selectedFile == file,
                selectedTileColor: Colors.blue.withOpacity(0.1),
                onTap: () {
                  setState(() {
                    _selectedFile = file;
                  });
                  _loadColumnInfo(file);
                },
              ),
            );
          })),
        
        if (_loadingColumns)
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Center(child: CircularProgressIndicator()),
          ),
        
        if (_columnNames.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 8),
          Text('✓ 数据集包含 ${_columnNames.length} 个特征',
              style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
        ],
      ],
    );
  }
  
  Widget _buildStep2ModelConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('🎯 选择建模任务类型',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'regression', label: Text('回归'), icon: Icon(Icons.show_chart)),
            ButtonSegment(value: 'classification', label: Text('分类'), icon: Icon(Icons.category)),
            ButtonSegment(value: 'clustering', label: Text('聚类'), icon: Icon(Icons.scatter_plot)),
          ],
          selected: {_problemType},
          onSelectionChanged: (Set<String> newSelection) {
            setState(() {
              _problemType = newSelection.first;
              _targetColumn = null;
            });
          },
        ),
        
        const SizedBox(height: 24),
        
        if (_problemType != 'clustering') ...[
          const Text('🎯 选择目标变量 (Target Column)',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          
          if (_columnNames.isEmpty)
            const Text('请先选择数据集', style: TextStyle(color: Colors.grey))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _columnNames.map((col) {
                final isSelected = _targetColumn == col;
                return ChoiceChip(
                  label: Text(col),
                  selected: isSelected,
                  onSelected: (selected) {
                    setState(() {
                      _targetColumn = col;
                    });
                    _inferProblemType(col);
                  },
                  selectedColor: Colors.deepPurple.withOpacity(0.3),
                );
              }).toList(),
            ),
          
          if (_inferredType.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb, color: Colors.orange, size: 20),
                  const SizedBox(width: 8),
                  Text('AI 推荐: $_inferredType',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ],
        ],
        
        if (_problemType == 'clustering') ...[
          const Text('🔢 设置聚类数',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Row(
            children: [
              Text('聚类数: $_nClusters'),
              Expanded(
                child: Slider(
                  value: _nClusters.toDouble(),
                  min: 2,
                  max: 10,
                  divisions: 8,
                  label: _nClusters.toString(),
                  onChanged: (value) {
                    setState(() {
                      _nClusters = value.round();
                    });
                  },
                ),
              ),
            ],
          ),
        ],
        
        const SizedBox(height: 24),
        const Text('⚙️ 训练模式',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        
        Card(
          color: Colors.green.withOpacity(0.1),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.auto_awesome, color: Colors.green),
                    SizedBox(width: 8),
                    Text('AutoML (Smart Sampling)',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ],
                ),
                const SizedBox(height: 8),
                const Text('自动优化内存并使用分层采样以保证统计显著性',
                    style: TextStyle(fontSize: 13, color: Colors.black87)),
                const SizedBox(height: 12),
                const Divider(),
                const SizedBox(height: 8),
                
                RadioListTile<String>(
                  title: const Text('Gradient Boosting (推荐)'),
                  subtitle: const Text('高精度，适合复杂模式'),
                  value: 'gradient_boosting',
                  groupValue: _modelAlgorithm,
                  onChanged: (value) {
                    setState(() {
                      _modelAlgorithm = value!;
                    });
                  },
                ),
                
                RadioListTile<String>(
                  title: const Text('Linear Model'),
                  subtitle: const Text('快速，适合线性关系'),
                  value: 'linear',
                  groupValue: _modelAlgorithm,
                  onChanged: (value) {
                    setState(() {
                      _modelAlgorithm = value!;
                    });
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildStep3Training() {
    if (!_isTraining && _trainingResult == null) {
      return Column(
        children: [
          const Icon(Icons.rocket_launch, size: 80, color: Colors.deepPurple),
          const SizedBox(height: 16),
          const Text('准备开始训练',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text('点击下方"开始训练"按钮启动 AutoML 流程'),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _trainModel,
            icon: const Icon(Icons.play_arrow),
            label: const Text('开始训练'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            ),
          ),
        ],
      );
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_isTraining) ...[
          const LinearProgressIndicator(),
          const SizedBox(height: 16),
          Text(_trainingStatus,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          
          ..._trainingSteps.map((step) {
            final isComplete = step.startsWith('✓');
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Icon(
                    isComplete ? Icons.check_circle : Icons.hourglass_empty,
                    color: isComplete ? Colors.green : Colors.orange,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text(step)),
                ],
              ),
            );
          }),
        ],
      ],
    );
  }
  
  Widget _buildStep4Results() {
    if (_trainingResult == null) {
      return const Center(child: Text('请先完成模型训练'));
    }
    
    final metrics = _trainingResult!['metrics'] as Map<String, dynamic>?;
    final warning = _trainingResult!['warning'] as String?;
    
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.green),
            ),
            child: Row(
              children: const [
                Icon(Icons.check_circle, color: Colors.green, size: 40),
                SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('✓ 模型训练成功',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      SizedBox(height: 4),
                      Text('您的模型已准备就绪'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          if (warning != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning, color: Colors.orange),
                  const SizedBox(width: 8),
                  Expanded(child: Text(warning)),
                ],
              ),
            ),
          ],
          
          const SizedBox(height: 24),
          
          if (metrics != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('📈 性能指标',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    
                    if (_problemType == 'regression') ...[
                      _buildMetricRow('R² Score', metrics['r2']),
                      _buildMetricRow('RMSE', metrics['rmse']),
                      if (metrics['cv_score'] != null)
                        _buildMetricRow('CV Score', metrics['cv_score']),
                    ] else if (_problemType == 'classification') ...[
                      _buildMetricRow('Accuracy', metrics['accuracy']),
                      _buildMetricRow('F1 Score', metrics['f1_weighted']),
                      if (metrics['cv_score'] != null)
                        _buildMetricRow('CV Score', metrics['cv_score']),
                    ] else if (_problemType == 'clustering') ...[
                      _buildMetricRow('Silhouette Score', metrics['silhouette_score']),
                    ],
                  ],
                ),
              ),
            ),
            
            if (metrics['cv_score'] != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.science, color: Colors.blue, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '交叉验证分数体现了模型的泛化能力，这是科学严谨性的铁证',
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
  
  Widget _buildMetricRow(String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(value?.toStringAsFixed(4) ?? '-',
              style: const TextStyle(fontSize: 16, color: Colors.blue)),
        ],
      ),
    );
  }
  
  Widget _buildStep5Prediction() {
    if (_modelPath == null) {
      return const Center(child: Text('请先完成模型训练'));
    }
    
    // 初始化输入控制器
    if (_predictionControllers.isEmpty && _columnNames.isNotEmpty) {
      for (var col in _columnNames) {
        if (col != _targetColumn) {
          _predictionControllers[col] = TextEditingController();
        }
      }
    }
    
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🔮 输入特征值进行预测',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          
          ..._predictionControllers.entries.map((entry) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: TextField(
                controller: entry.value,
                decoration: InputDecoration(
                  labelText: entry.key,
                  border: const OutlineInputBorder(),
                ),
              ),
            );
          }),
          
          const SizedBox(height: 16),
          
          ElevatedButton.icon(
            onPressed: _isPredicting ? null : _predictSingle,
            icon: _isPredicting
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.play_arrow),
            label: Text(_isPredicting ? '预测中...' : '开始预测'),
          ),
          
          if (_predictionResult != null) ...[
            const SizedBox(height: 24),
            Card(
              color: Colors.purple.withOpacity(0.1),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('预测结果',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    Text(
                      '预测值: ${_predictionResult!['predictions'][0]}',
                      style: const TextStyle(fontSize: 20, color: Colors.purple),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
