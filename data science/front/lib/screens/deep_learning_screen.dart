import 'package:flutter/material.dart';
import '../config/app_theme.dart';
import '../services/api_service.dart';
import '../widgets/common/animated_glass_card.dart';
import '../widgets/responsive_wrapper.dart';

class DeepLearningScreen extends StatefulWidget {
  final String? storagePath;
  
  const DeepLearningScreen({
    super.key, 
    this.storagePath,
  });

  @override
  State<DeepLearningScreen> createState() => _DeepLearningScreenState();
}

class _DeepLearningScreenState extends State<DeepLearningScreen> {
  // 状态变量
  bool _isTraining = false;
  String _trainLogs = ''; // 模拟日志
  
  // 表单参数
  String _modelType = 'lstm';
  int _epochs = 50;
  int _windowSize = 24;
  int _batchSize = 32;
  
  // 模拟文件路径 (在实际应用中应从上一页传递或选择)
  final _storagePathController = TextEditingController(text: 'data/sample.csv');

  @override
  void dispose() {
    _storagePathController.dispose();
    super.dispose();
  }

  Future<void> _startTraining() async {
    setState(() {
      _isTraining = true;
      _trainLogs = 'Initializing training environment on Cloud Run...\n';
    });
    
    // 模拟日志流
    _addLog('Allocating resources (4 CPU, 8GB RAM)...');
    await Future.delayed(const Duration(milliseconds: 800));
    _addLog('Loading heavy libraries (TensorFlow 2.15.0)...');
    
    try {
      final result = await ApiService.trainDeepModel(
        storagePath: widget.storagePath ?? 'demo_data.csv',
        modelType: _modelType,
        epochs: _epochs,
        batchSize: _batchSize,
        windowSize: _windowSize,
        targetColumn: 'Load', // Default to 'Load' for energy demo
      );
      
      _addLog('Training completed successfully!');
      _addLog('Metrics: ${result['metrics']}');
      
      setState(() {
        _isTraining = false;
      });
      
    } catch (e) {
      _addLog('Error: $e');
      setState(() {
        _isTraining = false;
      });
    }
  }
  
  void _addLog(String log) {
    setState(() {
      _trainLogs += '[${DateTime.now().toIso8601String().substring(11, 19)}] $log\n';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('深度学习实验室'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        flexibleSpace: Opacity(
          opacity: 0.8,
          child: Container(
            decoration: const BoxDecoration(
              gradient: AppColors.deepLearningGradient,
            ),
            child: Utils.glassFilter(),
          ),
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppColors.backgroundGradient,
        ),
        child: SafeArea(
          child: ResponsiveWrapper(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _buildHeader(),
                  const SizedBox(height: 24),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // 左侧配置面板
                      Expanded(flex: 4, child: _buildConfigPanel()),
                      const SizedBox(width: 24),
                      // 右侧终端/结果
                      Expanded(flex: 6, child: _buildTerminalPanel()),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildHeader() {
    return AnimatedGlassCard(
      enableHover: false,
      gradientBorder: AppColors.deepLearningGradient,
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF8B5CF6).withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
            ),
            child: const Icon(Icons.psychology_rounded, size: 32, color: Color(0xFF8B5CF6)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Time Series Forecasting', style: AppTextStyles.h3),
                Text(
                  'Powered by TensorFlow on Cloud Run (Heavy Core)', 
                  style: AppTextStyles.bodySmall,
                ),
              ],
            ),
          ),
          // Cloud Run Status Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.successLight,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
              border: Border.all(color: AppColors.success),
            ),
            child: Row(
              children: [
                const Icon(Icons.cloud_done_rounded, size: 16, color: AppColors.success),
                const SizedBox(width: 8),
                Text(
                  'Cloud Run Active',
                  style: AppTextStyles.labelMedium.copyWith(color: AppColors.success),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfigPanel() {
    return AnimatedGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Model Configuration', style: AppTextStyles.h4),
          const SizedBox(height: 20),
          
          // Model Type
          _buildDropdown('Model Architecture', _modelType, ['lstm', 'gru'], (val) {
            setState(() => _modelType = val!);
          }),
          const SizedBox(height: 16),
          
          // Epochs
          _buildSlider('Epochs', _epochs.toDouble(), 10, 200, (val) {
            setState(() => _epochs = val.toInt());
          }),
          
          // Window Size
          _buildSlider('Lookback Window', _windowSize.toDouble(), 12, 168, (val) {
            setState(() => _windowSize = val.toInt());
          }),
          
          // Batch Size
          _buildDropdown('Batch Size', _batchSize.toString(), ['16', '32', '64', '128'], (val) {
            setState(() => _batchSize = int.parse(val!));
          }),
          
          const SizedBox(height: 32),
          
          // Train Button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _isTraining ? null : _startTraining,
              icon: _isTraining 
                  ? const SizedBox(width:20, height:20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) 
                  : const Icon(Icons.play_arrow_rounded),
              label: Text(_isTraining ? 'Training in Progress...' : 'Start Cloud Training'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF8B5CF6), // Custom Purple
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildTerminalPanel() {
    return AnimatedGlassCard(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Terminal Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.05),
              border: const Border(bottom: BorderSide(color: AppColors.glassBorder)),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal_rounded, size: 20, color: AppColors.textSecondary),
                const SizedBox(width: 8),
                Text('Real-time Logs', style: AppTextStyles.labelLarge),
                const Spacer(),
                if (_isTraining)
                  const SizedBox(
                    width: 12, height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
          // Terminal Body
          Container(
            height: 400,
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B), // Slate 800
            child: SingleChildScrollView(
              reverse: true, // Auto scroll to bottom
              child: Text(
                _trainLogs.isEmpty ? 'Ready to train...' : _trainLogs,
                style: AppTextStyles.codeFont.copyWith(
                  color: const Color(0xFF34D399), // Emerald 400
                  fontSize: 13,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildDropdown(String label, String value, List<String> items, Function(String?) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.labelMedium),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              items: items.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildSlider(String label, double value, double min, double max, Function(double) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTextStyles.labelMedium),
            Text(value.toInt().toString(), style: AppTextStyles.labelLarge.copyWith(color: AppColors.primary)),
          ],
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          activeColor: const Color(0xFF8B5CF6),
          onChanged: onChanged,
        ),
      ],
    );
  }
}

// 简单的工具类，如果项目中没有
class Utils {
  static Widget glassFilter() {
    return const SizedBox(); // Placeholder if not strictly needed in AppBar
  }
}
