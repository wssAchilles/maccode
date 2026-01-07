/// 能源优化仪表盘 - Glassmorphism 设计
/// 交互式能源调度优化界面
library;

import 'dart:ui';
import 'package:flutter/material.dart';

import 'package:percent_indicator/percent_indicator.dart';
import 'package:intl/intl.dart';
import '../config/app_theme.dart';
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
  // 注意：负载规模约 150-300 kW (微网/商业楼宇级)
  double _batteryCapacity = 500; // kWh (商业储能)
  double _maxPower = 200; // kW
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
      final result = await ApiService.runOptimization(
        initialSoc: _initialSoc,
        targetDate: _selectedDate,
        batteryCapacity: _batteryCapacity,
        batteryPower: _maxPower,
        temperatureAdjust: _temperatureAdjust,
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
        backgroundColor: AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
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

                if (_result!.optimization!.diagnostics != null ||
                    _result!.optimization!.constraintHits != null) ...[
                  const SizedBox(height: 12),
                  _buildSolverDiagnosticsCard(_result!.optimization!),
                ],
                
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

  /// 1. 顶部控制卡片 - 交互式优化沙盒 (Glassmorphism)
  Widget _buildControlPanel() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
            border: Border.all(color: Colors.white.withValues(alpha: 0.3)),
            boxShadow: AppDecorations.shadowMd,
          ),
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                    ),
                    child: const Icon(Icons.tune_rounded, color: AppColors.primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '优化沙盒',
                      style: AppTextStyles.h3,
                    ),
                  ),
                  // 高级参数展开按钮
                  TextButton.icon(
                    onPressed: () => setState(() => _showAdvancedParams = !_showAdvancedParams),
                    icon: Icon(
                      _showAdvancedParams ? Icons.expand_less : Icons.expand_more,
                      size: 20,
                      color: AppColors.textMuted,
                    ),
                    label: Text(
                      _showAdvancedParams ? '收起' : '高级',
                      style: AppTextStyles.labelMedium,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
            
              // ========== 场景选择 ==========
              Text('快速场景', style: AppTextStyles.labelMedium.copyWith(color: AppColors.textMuted)),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildScenarioChip('summer', '夏季高温', AppColors.warning, Icons.wb_sunny_rounded),
                  _buildScenarioChip('winter', '冬季寒潮', AppColors.info, Icons.ac_unit_rounded),
                  _buildScenarioChip('overtime', '夜间加班', const Color(0xFF8B5CF6), Icons.nightlight_round),
                ],
              ),
              
              Divider(height: 32, color: AppColors.border),
            
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
              
              // 电池容量滑块 (商业级储能)
              _buildSliderRow(
                icon: Icons.battery_full,
                iconColor: Colors.blue,
                label: '电池容量 (商业微网)',
                value: _batteryCapacity,
                min: 100,
                max: 2000,
                divisions: 19,
                displayValue: '${_batteryCapacity.toInt()} kWh',
                onChanged: (v) => setState(() => _batteryCapacity = v),
              ),
              
              const SizedBox(height: 16),
              
              // 最大功率滑块 (商业级)
              _buildSliderRow(
                icon: Icons.flash_on,
                iconColor: Colors.amber,
                label: '最大功率 (微网级)',
                value: _maxPower,
                min: 50,
                max: 1000,
                divisions: 19,
                displayValue: '${_maxPower.toInt()} kW',
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
            
              const SizedBox(height: 24),
            
              // 开始优化按钮 (CTA 橙色)
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : _runOptimization,
                  icon: _isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                        )
                      : const Icon(Icons.bolt_rounded, size: 22),
                  label: Text(
                    _isLoading ? '优化中...' : '开始智能调度',
                    style: AppTextStyles.button,
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.cta,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                    ),
                    elevation: 0,
                  ),
                ),
              ),
            
              // 参数摘要
              if (_showAdvancedParams || _selectedScenario != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: AppColors.textMuted, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${_batteryCapacity.toInt()}kWh | ${_maxPower.toInt()}kW | ${(_initialSoc * 100).toInt()}%'
                          '${_temperatureAdjust != 0 ? " | ${_temperatureAdjust >= 0 ? "+" : ""}${_temperatureAdjust.toInt()}°C" : ""}',
                          style: AppTextStyles.bodySmall,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
  
  /// 场景选择芯片 (无 emoji)
  Widget _buildScenarioChip(String id, String label, Color color, IconData icon) {
    final isSelected = _selectedScenario == id;
    return FilterChip(
      avatar: Icon(
        icon,
        size: 16,
        color: isSelected ? Colors.white : color,
      ),
      label: Text(label, style: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        color: isSelected ? Colors.white : AppColors.textPrimary,
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
                break;
            }
            _showAdvancedParams = true; // 展开显示参数变化
          }
        });
      },
      backgroundColor: color.withValues(alpha: 0.1),
      selectedColor: color,
      checkmarkColor: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        side: BorderSide(color: isSelected ? color : color.withValues(alpha: 0.3)),
      ),
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
              inactiveColor: iconColor.withValues(alpha: 0.2),
              onChanged: _isLoading ? null : onChanged,
            ),
          ),
        ),
        Container(
          width: 70,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.1),
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
              
              // 核心指标展示
              if (modelInfo.metrics != null)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      // R2 Score (圆形进度条)
                      Expanded(
                        child: Column(
                          children: [
                            CircularPercentIndicator(
                              radius: 40.0,
                              lineWidth: 8.0,
                              percent: (modelInfo.metrics!.r2Score ?? 0).clamp(0.0, 1.0),
                              center: Text(
                                "${((modelInfo.metrics!.r2Score ?? 0) * 100).toStringAsFixed(0)}%",
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.purple[700],
                                ),
                              ),
                              progressColor: (modelInfo.metrics!.r2Score ?? 0) > 0.8 
                                  ? Colors.green 
                                  : Colors.orange,
                              backgroundColor: Colors.purple[50]!,
                              circularStrokeCap: CircularStrokeCap.round,
                              animation: true,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              "R² Score",
                              style: TextStyle(
                                color: Colors.grey[700],
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                      
                      const SizedBox(width: 16),
                      
                      // MAPE (线性进度条)
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  "MAPE (误差)",
                                  style: TextStyle(
                                    color: Colors.grey[700],
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                                Text(
                                  "${((modelInfo.metrics!.mape ?? 0) * 100).toStringAsFixed(1)}%",
                                  style: TextStyle(
                                    color: (modelInfo.metrics!.mape ?? 0) < 0.1 
                                        ? Colors.green 
                                        : Colors.orange,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            LinearPercentIndicator(
                              lineHeight: 8.0,
                              percent: (1.0 - (modelInfo.metrics!.mape ?? 0)).clamp(0.0, 1.0),
                              progressColor: (modelInfo.metrics!.mape ?? 0) < 0.1 
                                  ? Colors.green 
                                  : Colors.orange,
                              backgroundColor: Colors.purple[50]!,
                              barRadius: const Radius.circular(4),
                              animation: true,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              (modelInfo.metrics!.mape ?? 0) < 0.1 ? "精度优良" : "精度一般",
                              style: TextStyle(
                                fontSize: 10,
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                )
              else
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Text("暂无详细性能指标"),
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
                      modelInfo.usedAutoSelection 
                          ? modelInfo.winnerModel 
                          : 'Random Forest',
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
              
              // 自动模型选择信息卡片 (新增)
              if (modelInfo.usedAutoSelection) ...[
                const SizedBox(height: 16),
                _buildAutoSelectionCard(modelInfo),
              ],
              
              // 训练配置信息 (新增)
              if (modelInfo.trainingConfig != null) ...[
                const SizedBox(height: 16),
                _buildOptimizationConfigCard(modelInfo),
              ],
              
              // 验证与数据覆盖
              if (modelInfo.validationSummary != null || modelInfo.dataCoverage != null) ...[
                const SizedBox(height: 16),
                _buildValidationSummaryCard(modelInfo),
              ],
              
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

  /// 构建自动模型选择信息卡片
  Widget _buildAutoSelectionCard(ModelInfo modelInfo) {
    final autoSelection = modelInfo.autoSelection!;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.green[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行
          Row(
            children: [
              Icon(Icons.auto_awesome, color: Colors.green[700], size: 18),
              const SizedBox(width: 8),
              Text(
                '🤖 自动模型选择',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.green[900],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.green[600],
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '已启用',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          // 详情网格
          Row(
            children: [
              Expanded(
                child: _buildAutoSelectionItem(
                  '🏆 胜出模型',
                  autoSelection.winner,
                  Colors.amber[700]!,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildAutoSelectionItem(
                  '📈 性能提升',
                  autoSelection.improvementOverBaseline,
                  Colors.green[700]!,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildAutoSelectionItem(
                  '🔬 验证方法',
                  autoSelection.validationMethodFormatted,
                  Colors.blue[700]!,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildAutoSelectionItem(
                  '📊 候选模型',
                  '${autoSelection.candidatesEvaluated.length} 个',
                  Colors.purple[700]!,
                ),
              ),
            ],
          ),
          
          // 展开查看所有候选模型得分
          if (autoSelection.allScores != null && autoSelection.allScores!.isNotEmpty) ...[
            const SizedBox(height: 12),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              title: Text(
                '查看所有候选模型得分',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.green[700],
                  fontWeight: FontWeight.w500,
                ),
              ),
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Column(
                    children: autoSelection.allScores!.entries.map((entry) {
                      final scores = entry.value as Map<String, dynamic>;
                      final mae = scores['mae'] ?? 0.0;
                      final isWinner = entry.key == autoSelection.winner;
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            if (isWinner)
                              const Text('🏆 ', style: TextStyle(fontSize: 12))
                            else
                              const SizedBox(width: 18),
                            Expanded(
                              child: Text(
                                entry.key,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: isWinner ? FontWeight.bold : FontWeight.normal,
                                  color: isWinner ? Colors.amber[800] : Colors.grey[700],
                                ),
                              ),
                            ),
                            Text(
                              'MAE: ${mae.toStringAsFixed(2)} kW',
                              style: TextStyle(
                                fontSize: 11,
                                color: isWinner ? Colors.green[700] : Colors.grey[600],
                                fontWeight: isWinner ? FontWeight.bold : FontWeight.normal,
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  /// 构建优化配置信息卡片
  Widget _buildOptimizationConfigCard(ModelInfo modelInfo) {
    if (modelInfo.trainingConfig == null) return const SizedBox();
    
    final config = modelInfo.trainingConfig!;
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.indigo[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.indigo[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.tune, color: Colors.indigo[700], size: 18),
              const SizedBox(width: 8),
              Text(
                '⚙️ 训练配置',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.indigo[900],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildConfigChip(
                'Log1p 变换', 
                config.useLogTransform ?? false,
                Icons.functions,
              ),
              _buildConfigChip(
                '异常值剔除', 
                config.removeOutliers ?? false,
                Icons.filter_alt,
              ),
              _buildConfigChip(
                '超参数调优', 
                config.tuneHyperparameters ?? false,
                Icons.explore,
              ),
               _buildConfigChip(
                '时序交叉验证', 
                config.useTimeSeriesCV ?? false,
                Icons.timeline,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConfigChip(String label, bool enabled, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: enabled ? Colors.white : Colors.grey[200],
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: enabled ? Colors.indigo[200]! : Colors.grey[300]!,
        ),
        boxShadow: enabled ? [
          BoxShadow(
            color: Colors.indigo.withValues(alpha: 0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          )
        ] : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon, 
            size: 14, 
            color: enabled ? Colors.indigo[600] : Colors.grey[500]
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: enabled ? FontWeight.bold : FontWeight.normal,
              color: enabled ? Colors.indigo[800] : Colors.grey[600],
            ),
          ),
          const SizedBox(width: 4),
          Icon(
            enabled ? Icons.check_circle : Icons.cancel,
            size: 14,
            color: enabled ? Colors.green[600] : Colors.grey[400],
          ),
        ],
      ),
    );
  }

  Widget _buildAutoSelectionItem(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildValidationSummaryCard(ModelInfo modelInfo) {
    final validation = modelInfo.validationSummary;
    final coverage = modelInfo.dataCoverage;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.indigo[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.indigo[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.verified, color: Colors.indigo[700], size: 18),
              const SizedBox(width: 8),
              const Text(
                '验证与数据覆盖',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (validation != null) ...[
            Row(
              children: [
                Expanded(
                  child: _buildModelStatItem(
                    Icons.rule,
                    '验证方式',
                    validation.method ?? 'N/A',
                    Colors.indigo[800]!,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildModelStatItem(
                    Icons.repeat,
                    '折数',
                    validation.cvFolds?.toString() ?? '—',
                    Colors.deepPurple[700]!,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _buildModelStatItem(
                    Icons.assessment,
                    'CV MAE',
                    validation.cvMaeMean != null
                        ? '${validation.cvMaeMean!.toStringAsFixed(2)} kW ± ${validation.cvMaeStd?.toStringAsFixed(2) ?? "0"}'
                        : 'N/A',
                    Colors.teal[700]!,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildModelStatItem(
                    Icons.check_circle,
                    'Holdout MAE',
                    validation.holdoutMae != null
                        ? '${validation.holdoutMae!.toStringAsFixed(2)} kW'
                        : 'N/A',
                    Colors.blueGrey[700]!,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
          ],
          if (coverage != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.indigo[100]!),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.date_range, size: 16, color: Colors.indigo[700]),
                      const SizedBox(width: 6),
                      Text(
                        '数据覆盖区间',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.indigo[800],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${coverage.start ?? "N/A"}  至  ${coverage.end ?? "N/A"}',
                    style: TextStyle(
                      color: Colors.grey[800],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '跨度: ${coverage.spanDays != null ? "${coverage.spanDays} 天" : "未知"} · 样本: ${coverage.rows ?? 0}',
                    style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSolverDiagnosticsCard(OptimizationData optimization) {
    final diag = optimization.diagnostics;
    final hits = optimization.constraintHits;
    if (diag == null && hits == null) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.speed, color: Colors.blue[700]),
                const SizedBox(width: 8),
                const Text(
                  '求解器健康度',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildModelStatItem(
                    Icons.timer,
                    '求解耗时',
                    diag?.runtimeLabel ?? 'N/A',
                    Colors.blue[700]!,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildModelStatItem(
                    Icons.data_usage,
                    'MIP Gap',
                    diag?.mipGap != null ? '${(diag!.mipGap! * 100).toStringAsFixed(2)}%' : 'N/A',
                    Colors.deepOrange[700]!,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildModelStatItem(
                    Icons.account_tree,
                    'Node',
                    diag?.nodeCount?.toString() ?? '—',
                    Colors.teal[700]!,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildModelStatItem(
                    Icons.loop,
                    '迭代',
                    diag?.iterCount?.toString() ?? '—',
                    Colors.indigo[700]!,
                  ),
                ),
              ],
            ),
            if (hits != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.battery_alert,
                      'SOC 下限命中',
                      '${hits.socMinHits} 次',
                      Colors.red[600]!,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.battery_full,
                      'SOC 上限命中',
                      '${hits.socMaxHits} 次',
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
                      Icons.flash_on,
                      '充电功率封顶',
                      '${hits.maxChargeHits} 小时',
                      Colors.orange[700]!,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildModelStatItem(
                      Icons.bolt,
                      '放电功率封顶',
                      '${hits.maxDischargeHits} 小时',
                      Colors.blueGrey[700]!,
                    ),
                  ),
                ],
              ),
            ],
          ],
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
                  color: savingsDiff > 0 ? Colors.green.withValues(alpha: 0.2) : Colors.red.withValues(alpha: 0.2),
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
                  color: iconColor.withValues(alpha: 0.2),
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
}
