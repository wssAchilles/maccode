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
  String? _errorMessage;
  DateTime? _selectedDate;

  @override
  void initState() {
    super.initState();
    // 默认选择明天
    _selectedDate = DateTime.now().add(const Duration(days: 1));
  }

  /// 执行优化
  Future<void> _runOptimization() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _result = null;
    });

    try {
      final result = await ApiService.runOptimization(
        initialSoc: _initialSoc,
        targetDate: _selectedDate,
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
              
              // 4. 关键指标卡片
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

  /// 1. 顶部控制卡片
  Widget _buildControlPanel() {
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
                Icon(Icons.settings, color: Colors.blue[700], size: 24),
                const SizedBox(width: 8),
                const Text(
                  '优化参数配置',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            
            // 初始电量滑块
            Row(
              children: [
                const Icon(Icons.battery_charging_full, color: Colors.green),
                const SizedBox(width: 8),
                const Text(
                  '初始电量 (Initial SOC)',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: _initialSoc,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    label: '${(_initialSoc * 100).toInt()}%',
                    activeColor: Colors.blue[700],
                    onChanged: _isLoading
                        ? null
                        : (value) {
                            setState(() {
                              _initialSoc = value;
                            });
                          },
                  ),
                ),
                const SizedBox(width: 16),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.blue[50],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${(_initialSoc * 100).toInt()}%',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue[700],
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 20),
            
            // 日期选择
            Row(
              children: [
                const Icon(Icons.calendar_today, color: Colors.orange),
                const SizedBox(width: 8),
                const Text(
                  '目标日期',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            InkWell(
              onTap: _isLoading ? null : () => _selectDate(context),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey[300]!),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _selectedDate != null
                          ? DateFormat('yyyy-MM-dd').format(_selectedDate!)
                          : '选择日期',
                      style: const TextStyle(fontSize: 16),
                    ),
                    Icon(Icons.arrow_drop_down, color: Colors.grey[600]),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // 开始优化按钮
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _runOptimization,
                icon: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.bolt, size: 24),
                label: Text(
                  _isLoading ? '优化中...' : '开始智能调度',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue[700],
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 2,
                ),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // 提示信息
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.blue[700], size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '系统将基于负载预测和电价优化充放电策略',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.blue[900],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
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

  /// 4. 关键指标卡片
  Widget _buildKeyMetrics(OptimizationData optimization) {
    final summary = optimization.summary;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.analytics, color: Colors.blue[700], size: 24),
            const SizedBox(width: 8),
            const Text(
              '关键指标',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
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
