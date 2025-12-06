/// 能源优化仪表盘
/// 交互式能源调度优化界面
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../models/optimization_result.dart';
import '../widgets/power_chart_widget.dart';
import '../widgets/soc_chart_widget.dart';
import '../widgets/responsive_wrapper.dart';
import '../widgets/analysis/feature_importance_chart.dart';
import '../utils/responsive_helper.dart';
import '../config/constants.dart';

class ModelingScreen extends StatefulWidget {
  const ModelingScreen({super.key});

  @override
  State<ModelingScreen> createState() => _ModelingScreenState();
}

class _ModelingScreenState extends State<ModelingScreen> {
  // 状态变量
  bool _isLoading = false;
  double _initialSoc = AppConstants.defaultInitialSoc; // 默认 50%
  OptimizationResponse? _result;
  OptimizationResponse? _previousResult; // 用于对比
  String? _errorMessage;
  DateTime? _selectedDate;
  
  // 🔋 电池参数 (方案一：交互式优化沙盒)
  // 注意：负载规模约 20000-30000 kW，需要工业级储能
  double _batteryCapacity = 5000; // kWh (工业级储能)
  double _maxPower = 2000; // kW
  bool _showAdvancedParams = false; // 是否展开高级参数
  
  // 🌡️ 场景模拟 (方案二)
  String? _selectedScenario; // 'summer', 'winter', 'overtime'
  
  // 🔮 What-If 预测 (方案三)
  double _temperatureAdjust = 0.0; // -5 ~ +5 度

  @override
  void initState() {
    super.initState();
    // 默认选择明天
    _selectedDate = DateTime.now().add(const Duration(days: 1));
  }

  /// 执行优化
  Future<void> _runOptimization({bool saveForComparison = true}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      if (saveForComparison && _result != null) {
        _previousResult = _result; // 保存上次结果用于对比
      }
      _result = null;
    });

    try {
      // 构建温度预测（如果有 What-If 调整）
      List<double>? tempForecast;
      if (_temperatureAdjust != 0.0) {
        // 基础温度 25°C，加上调整值
        tempForecast = List.generate(24, (i) => 25.0 + _temperatureAdjust);
      }
      
      final result = await ApiService.runOptimization(
        initialSoc: _initialSoc,
        targetDate: _selectedDate,
        batteryCapacity: _batteryCapacity,
        batteryPower: _maxPower,
        temperatureForecast: tempForecast,
      );

      if (mounted) {
        setState(() {
          _result = result;
          _isLoading = false;
        });

        if (result.isSuccess) {
          _showSuccessSnackBar('优化完成！节省 ${result.optimization?.summary.savingsFormatted ?? "0"}');
        } else {
          setState(() {
            _errorMessage = result.message ?? result.error ?? '优化失败';
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
        _showErrorSnackBar(_errorMessage!);
      }
    }
  }

  void _showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: Colors.red,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text(
          '⚡ 能源优化仪表盘',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        elevation: 0,
        backgroundColor: Colors.blue[700],
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showInfoDialog(),
            tooltip: '关于',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          if (!_isLoading && _initialSoc > 0) {
            await _runOptimization();
          }
        },
        child: ResponsiveWrapper(
          maxWidth: ResponsiveHelper.getMaxContentWidth(context),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: ResponsiveHelper.getPagePadding(context),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
              // 1. 顶部控制卡片
              _buildControlPanel(),
              
              const SizedBox(height: 16),
              
              // 2. 错误提示
              if (_errorMessage != null) _buildErrorCard(),
              
              // 3. 加载指示器
              if (_isLoading) _buildLoadingCard(),
              
              // 4. AI模型健康度卡片 (关键新增！)
              if (_result?.modelInfo != null) ...[
                const SizedBox(height: 16),
                _buildModelHealthCard(_result!.modelInfo!),
              ],
              
              // 5. 关键指标卡片
              if (_result?.optimization != null) ...[
                const SizedBox(height: 16),
                _buildKeyMetrics(_result!.optimization!),
                
                const SizedBox(height: 24),
                
                // 5. 电网交互策略图
                PowerChartWidget(
                  chartData: _result!.optimization!.chartData,
                ),
                
                const SizedBox(height: 16),
                
                // 6. 电池电量变化图
                SocChartWidget(
                  chartData: _result!.optimization!.chartData,
                ),
                
                const SizedBox(height: 16),
                
                // 7. 策略详情
                _buildStrategyDetails(_result!.optimization!),
                
                // 8. 模型可解释性 - 特征重要性图表
                if (_result?.modelExplainability != null) ...[
                  const SizedBox(height: 16),
                  ExpansionTile(
                    initiallyExpanded: false,
                    tilePadding: const EdgeInsets.symmetric(horizontal: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    collapsedShape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    backgroundColor: Colors.white,
                    collapsedBackgroundColor: Colors.white,
                    leading: Icon(Icons.psychology, color: Colors.purple[600]),
                    title: const Text(
                      '🔍 AI 预测解释',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    subtitle: Text(
                      '了解哪些因素影响了负载预测',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: FeatureImportanceChart(
                          featureImportance: _result!.modelExplainability!.featureImportance,
                          featureDescriptions: _result!.modelExplainability!.featureDescriptions,
                          interpretation: _result!.modelExplainability!.interpretation,
                        ),
                      ),
                    ],
                  ),
                ],
              ],
              
              // 空状态提示
              if (_result == null && !_isLoading && _errorMessage == null)
                _buildEmptyState(),
              
              const SizedBox(height: 32),
            ],
          ),
        ),
        ),
      ),
    );
  }

  /// 1. 顶部控制卡片 - 交互式优化沙盒
  Widget _buildControlPanel() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            Row(
              children: [
                Icon(Icons.tune, color: Colors.blue[700], size: 24),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    '🧪 优化沙盒',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                // 高级参数展开按钮
                TextButton.icon(
                  onPressed: () => setState(() => _showAdvancedParams = !_showAdvancedParams),
                  icon: Icon(
                    _showAdvancedParams ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                  ),
                  label: Text(_showAdvancedParams ? '收起' : '高级'),
                  style: TextButton.styleFrom(foregroundColor: Colors.grey[600]),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // ========== 场景选择 (方案二) ==========
            const Text('📊 快速场景', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.grey)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildScenarioChip('summer', '☀️ 夏季高温', Colors.orange),
                _buildScenarioChip('winter', '❄️ 冬季寒潮', Colors.blue),
                _buildScenarioChip('overtime', '🏭 夜间加班', Colors.purple),
              ],
            ),
            
            const Divider(height: 32),
            
            // ========== 初始电量滑块 ==========
            _buildSliderRow(
              icon: Icons.battery_charging_full,
              iconColor: Colors.green,
              label: '初始电量',
              value: _initialSoc,
              min: 0.0,
              max: 1.0,
              divisions: 20,
              displayValue: '${(_initialSoc * 100).toInt()}%',
              onChanged: (v) => setState(() => _initialSoc = v),
            ),
            
            // ========== 高级参数 (可折叠) ==========
            if (_showAdvancedParams) ...[
              const SizedBox(height: 16),
              
              // 电池容量滑块 (工业级储能)
              _buildSliderRow(
                icon: Icons.battery_full,
                iconColor: Colors.blue,
                label: '电池容量',
                value: _batteryCapacity,
                min: 1000,
                max: 10000,
                divisions: 9,
                displayValue: '${(_batteryCapacity / 1000).toStringAsFixed(1)} MWh',
                onChanged: (v) => setState(() => _batteryCapacity = v),
              ),
              
              const SizedBox(height: 16),
              
              // 最大功率滑块 (工业级)
              _buildSliderRow(
                icon: Icons.flash_on,
                iconColor: Colors.amber,
                label: '最大功率',
                value: _maxPower,
                min: 500,
                max: 5000,
                divisions: 9,
                displayValue: '${(_maxPower / 1000).toStringAsFixed(1)} MW',
                onChanged: (v) => setState(() => _maxPower = v),
              ),
              
              const SizedBox(height: 16),
              
              // What-If 温度调整 (方案三)
              _buildSliderRow(
                icon: Icons.thermostat,
                iconColor: Colors.red,
                label: '温度调整 (What-If)',
                value: _temperatureAdjust,
                min: -5.0,
                max: 5.0,
                divisions: 10,
                displayValue: '${_temperatureAdjust >= 0 ? "+" : ""}${_temperatureAdjust.toInt()}°C',
                onChanged: (v) => setState(() => _temperatureAdjust = v),
              ),
            ],
            
            const SizedBox(height: 16),
            
            // 日期选择
            Row(
              children: [
                const Icon(Icons.calendar_today, color: Colors.orange, size: 20),
                const SizedBox(width: 8),
                const Text('目标日期', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                const Spacer(),
                InkWell(
                  onTap: _isLoading ? null : () => _selectDate(context),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey[300]!),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _selectedDate != null
                              ? DateFormat('MM-dd').format(_selectedDate!)
                              : '选择',
                          style: const TextStyle(fontSize: 14),
                        ),
                        const SizedBox(width: 4),
                        Icon(Icons.arrow_drop_down, color: Colors.grey[600], size: 20),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 20),
            
            // 开始优化按钮
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _runOptimization,
                icon: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.bolt, size: 22),
                label: Text(
                  _isLoading ? '优化中...' : '🚀 开始智能调度',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue[700],
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 2,
                ),
              ),
            ),
            
            // 参数摘要
            if (_showAdvancedParams || _selectedScenario != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.grey[600], size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '🔋 ${(_batteryCapacity / 1000).toStringAsFixed(1)}MWh | ⚡ ${(_maxPower / 1000).toStringAsFixed(1)}MW | 🔌 ${(_initialSoc * 100).toInt()}%'
                        '${_temperatureAdjust != 0 ? " | 🌡️ ${_temperatureAdjust >= 0 ? "+" : ""}${_temperatureAdjust.toInt()}°C" : ""}',
                        style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  /// 场景选择芯片
  Widget _buildScenarioChip(String id, String label, Color color) {
    final isSelected = _selectedScenario == id;
    return FilterChip(
      label: Text(label, style: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        color: isSelected ? Colors.white : Colors.grey[800],
      )),
      selected: isSelected,
      onSelected: _isLoading ? null : (selected) {
        setState(() {
          _selectedScenario = selected ? id : null;
          // 根据场景预设参数
          if (selected) {
            switch (id) {
              case 'summer':
                _temperatureAdjust = 5.0; // 高温
                break;
              case 'winter':
                _temperatureAdjust = -5.0; // 低温
                break;
              case 'overtime':
                _temperatureAdjust = 0.0;
                // 可以在后端处理夜间负载增加
                break;
            }
            _showAdvancedParams = true; // 展开显示参数变化
          }
        });
      },
      backgroundColor: Colors.grey[200],
      selectedColor: color,
      checkmarkColor: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }
  
  /// 通用滑块行
  Widget _buildSliderRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required String displayValue,
    required ValueChanged<double> onChanged,
  }) {
    return Row(
      children: [
        Icon(icon, color: iconColor, size: 20),
        const SizedBox(width: 8),
        SizedBox(
          width: 100,
          child: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
        ),
        Expanded(
          child: SliderTheme(
            data: SliderTheme.of(context).copyWith(
              trackHeight: 4,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
            ),
            child: Slider(
              value: value,
              min: min,
              max: max,
              divisions: divisions,
              activeColor: iconColor,
              inactiveColor: iconColor.withOpacity(0.2),
              onChanged: _isLoading ? null : onChanged,
            ),
          ),
        ),
        Container(
          width: 70,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            displayValue,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: iconColor),
          ),
        ),
      ],
    );
  }

  /// 选择日期
  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now().add(const Duration(days: 1)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 7)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: Colors.blue[700]!,
              onPrimary: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );
    
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
    }
  }

  /// 2. 错误卡片
  Widget _buildErrorCard() {
    return Card(
      color: Colors.red[50],
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.red[300]!, width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(Icons.error_outline, color: Colors.red[700], size: 32),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '优化失败',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.red[900],
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _errorMessage ?? '未知错误',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.red[800],
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.close),
              color: Colors.red[700],
              onPressed: () {
                setState(() {
                  _errorMessage = null;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  /// 3. 加载卡片
  Widget _buildLoadingCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              '正在执行优化...',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '预计需要 30-60 秒',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 4. AI模型健康度卡片 - 核心展示"模型生命力"
  Widget _buildModelHealthCard(ModelInfo modelInfo) {
    return Card(
      elevation: 6,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.purple[200]!, width: 2),
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Colors.purple[50]!, Colors.blue[50]!],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题行
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.purple[600],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.psychology, color: Colors.white, size: 24),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '🧠 AI 模型状态',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          '机器学习预测引擎（眼睛）',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),
                  // 状态指示器
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: modelInfo.isValid ? Colors.green : Colors.orange,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      modelInfo.isValid ? '运行中' : '待训练',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 20),
              
              // 关键信息说明
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.8),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.purple[200]!),
                ),
                child: Row(
                  children: [
                    Icon(Icons.tips_and_updates, color: Colors.purple[700], size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '以下策略基于随机森林模型生成，模型实时学习气候和负载规律',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.purple[900],
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 16),
              
              // 模型详情网格
              Row(
                children: [
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.model_training,
                      '模型类型',
                      'Random Forest',
                      Colors.blue[700]!,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.storage,
                      '训练数据',
                      modelInfo.trainingSamples != null
                          ? '${modelInfo.trainingSamples} 样本'
                          : 'N/A',
                      Colors.green[700]!,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 12),
              
              Row(
                children: [
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.schedule,
                      '最近更新',
                      modelInfo.trainedAtFormatted,
                      Colors.orange[700]!,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.precision_manufacturing,
                      '预测精度 (MAE)',
                      modelInfo.maeFormatted,
                      Colors.purple[700]!,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // 数据源说明
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.cloud_download, color: Colors.blue[700], size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '数据来源: ${modelInfo.dataSource ?? "CAISO 实时流"}',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: Colors.blue[900],
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '模型每日凌晨自动重训，持续学习最新用电模式',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.blue[700],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModelStatItem(IconData icon, String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Colors.grey,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  /// 5. 关键指标卡片 - 增强版（方案一核心展示）
  Widget _buildKeyMetrics(OptimizationData optimization) {
    final summary = optimization.summary;
    
    // 计算与之前结果的差异（如果有）
    double? savingsDiff;
    if (_previousResult?.optimization != null) {
      final prevSavings = _previousResult!.optimization!.summary.savings;
      savingsDiff = summary.savings - prevSavings;
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.analytics, color: Colors.blue[700], size: 24),
            const SizedBox(width: 8),
            const Text(
              '💰 优化效果',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Spacer(),
            // 显示与之前结果的对比
            if (savingsDiff != null && savingsDiff.abs() > 0.01) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: savingsDiff > 0 ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      savingsDiff > 0 ? Icons.trending_up : Icons.trending_down,
                      size: 14,
                      color: savingsDiff > 0 ? Colors.green[700] : Colors.red[700],
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${savingsDiff > 0 ? "+" : ""}${savingsDiff.toStringAsFixed(2)}元 vs 上次',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: savingsDiff > 0 ? Colors.green[700] : Colors.red[700],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 12),
        
        // 三个指标卡片 - 响应式布局
        LayoutBuilder(
          builder: (context, constraints) {
            final isMobile = ResponsiveHelper.isMobile(context);
            
            if (isMobile) {
              // 移动端：垂直排列
              return Column(
                children: [
                  _buildMetricCard(
                    icon: Icons.savings,
                    iconColor: Colors.green,
                    label: '节省金额',
                    value: summary.savingsFormatted,
                    backgroundColor: Colors.green[50]!,
                    valueColor: Colors.green[700]!,
                  ),
                  const SizedBox(height: 12),
                  _buildMetricCard(
                    icon: Icons.percent,
                    iconColor: Colors.orange,
                    label: '节省比例',
                    value: summary.savingsPercentFormatted,
                    backgroundColor: Colors.orange[50]!,
                    valueColor: Colors.orange[700]!,
                  ),
                ],
              );
            } else {
              // 平板/桌面端：水平排列
              return Row(
                children: [
                  Expanded(
                    child: _buildMetricCard(
                      icon: Icons.savings,
                      iconColor: Colors.green,
                      label: '节省金额',
                      value: summary.savingsFormatted,
                      backgroundColor: Colors.green[50]!,
                      valueColor: Colors.green[700]!,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildMetricCard(
                      icon: Icons.percent,
                      iconColor: Colors.orange,
                      label: '节省比例',
                      value: summary.savingsPercentFormatted,
                      backgroundColor: Colors.orange[50]!,
                      valueColor: Colors.orange[700]!,
                    ),
                  ),
                ],
              );
            }
          },
        ),
        
        const SizedBox(height: 12),
        
        // 成本对比卡片
        Card(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.compare_arrows, color: Colors.blue[700]),
                    const SizedBox(width: 8),
                    const Text(
                      '成本对比',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                
                _buildCostComparisonRow(
                  '无电池成本',
                  summary.totalCostWithoutBattery,
                  Colors.grey,
                ),
                const SizedBox(height: 8),
                _buildCostComparisonRow(
                  '有电池成本',
                  summary.totalCostWithBattery,
                  Colors.blue,
                ),
                
                const Divider(height: 24),
                
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      '总计节省',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      summary.savingsFormatted,
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Colors.green[700],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String value,
    required Color backgroundColor,
    required Color valueColor,
  }) {
    return Card(
      elevation: 2,
      color: backgroundColor,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: iconColor, size: 32),
            const SizedBox(height: 12),
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCostComparisonRow(String label, double cost, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(fontSize: 14),
            ),
          ],
        ),
        Text(
          '¥${cost.toStringAsFixed(2)}',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  /// 7. 策略详情
  Widget _buildStrategyDetails(OptimizationData optimization) {
    final strategy = optimization.strategy;
    
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.schedule, color: Colors.blue[700], size: 24),
                const SizedBox(width: 8),
                const Text(
                  '⚡ 充放电策略',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // 充电时段
            _buildStrategyRow(
              icon: Icons.battery_charging_full,
              iconColor: Colors.green,
              label: '充电时段',
              value: strategy.chargingHoursFormatted,
              count: '${strategy.chargingCount} 小时',
              backgroundColor: Colors.green[50]!,
            ),
            
            const SizedBox(height: 12),
            
            // 放电时段
            _buildStrategyRow(
              icon: Icons.flash_on,
              iconColor: Colors.red,
              label: '放电时段',
              value: strategy.dischargingHoursFormatted,
              count: '${strategy.dischargingCount} 小时',
              backgroundColor: Colors.red[50]!,
            ),
            
            const SizedBox(height: 16),
            
            // 统计信息
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                children: [
                  _buildStatRow(
                    '总充电量',
                    '${optimization.summary.totalCharged.toStringAsFixed(2)} kWh',
                  ),
                  const Divider(height: 16),
                  _buildStatRow(
                    '总放电量',
                    '${optimization.summary.totalDischarged.toStringAsFixed(2)} kWh',
                  ),
                  const Divider(height: 16),
                  _buildStatRow(
                    '循环效率',
                    '${optimization.summary.cycleEfficiency.toStringAsFixed(1)}%',
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStrategyRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String value,
    required String count,
    required Color backgroundColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: iconColor, size: 20),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: iconColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  count,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: iconColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              color: Colors.grey[700],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 14),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  /// 空状态
  Widget _buildEmptyState() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(40.0),
        child: Column(
          children: [
            Icon(
              Icons.analytics_outlined,
              size: 80,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              '开始优化',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '调整初始电量参数，点击"开始智能调度"按钮',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 信息对话框
  void _showInfoDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.info, color: Colors.blue),
            SizedBox(width: 8),
            Text('关于能源优化'),
          ],
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '功能说明',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              Text('• 基于机器学习预测未来24小时能源负载'),
              Text('• 使用混合整数规划优化电池充放电策略'),
              Text('• 考虑峰谷电价，最小化总购电成本'),
              SizedBox(height: 16),
              Text(
                '电价时段',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              Text('• 谷时 (00:00-08:00, 22:00-24:00): 0.3 元/kWh'),
              Text('• 平时 (08:00-18:00): 0.6 元/kWh'),
              Text('• 峰时 (18:00-22:00): 1.0 元/kWh'),
              SizedBox(height: 16),
              Text(
                '电池参数',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              Text('• 容量: 13.5 kWh (Tesla Powerwall)'),
              Text('• 最大功率: 5.0 kW'),
              Text('• 充放电效率: 95%'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }
}
