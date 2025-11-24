/// 优化服务使用示例
/// 展示如何调用优化 API
library;

import 'api_service.dart';
import '../models/optimization_result.dart';

/// 优化服务使用示例类
class OptimizationServiceExample {
  /// 示例 1: 基础优化调用
  /// 
  /// 使用默认参数运行优化
  static Future<void> basicOptimization() async {
    try {
      print('执行基础优化...');
      
      final result = await ApiService.runOptimization(
        initialSoc: 0.5, // 初始电量 50%
      );

      if (result.isSuccess && result.optimization != null) {
        final opt = result.optimization!;
        print('优化成功！');
        print('状态: ${opt.status}');
        print('节省金额: ${opt.summary.savingsFormatted}');
        print('节省比例: ${opt.summary.savingsPercentFormatted}');
        print('充电时段: ${opt.strategy.chargingHoursFormatted}');
        print('放电时段: ${opt.strategy.dischargingHoursFormatted}');
      } else {
        print('优化失败: ${result.message ?? result.error}');
      }
    } catch (e) {
      print('优化出错: $e');
    }
  }

  /// 示例 2: 带温度预测的优化
  /// 
  /// 提供24小时温度预测数据
  static Future<void> optimizationWithTemperature() async {
    try {
      print('执行带温度预测的优化...');

      // 模拟温度预测数据 (夏季)
      final temperatureForecast = [
        24.0, 23.5, 23.0, 22.8, 22.5, 23.0, // 00:00-05:00
        24.0, 25.0, 26.5, 28.0, 29.5, 30.5, // 06:00-11:00
        31.0, 31.5, 31.8, 31.5, 31.0, 30.0, // 12:00-17:00
        28.5, 27.0, 26.0, 25.5, 25.0, 24.5, // 18:00-23:00
      ];

      final result = await ApiService.runOptimization(
        initialSoc: 0.6,
        temperatureForecast: temperatureForecast,
      );

      if (result.isSuccess && result.optimization != null) {
        final opt = result.optimization!;
        print('优化完成！');
        _printOptimizationDetails(opt);
      }
    } catch (e) {
      print('优化出错: $e');
    }
  }

  /// 示例 3: 指定日期的优化
  /// 
  /// 为特定日期进行优化
  static Future<void> optimizationForSpecificDate() async {
    try {
      print('执行指定日期的优化...');

      final targetDate = DateTime.now().add(const Duration(days: 2));

      final result = await ApiService.runOptimization(
        initialSoc: 0.5,
        targetDate: targetDate,
      );

      if (result.isSuccess && result.optimization != null) {
        print('优化日期: ${result.prediction?.targetDate}');
        _printOptimizationDetails(result.optimization!);
      }
    } catch (e) {
      print('优化出错: $e');
    }
  }

  /// 示例 4: 自定义电池参数
  /// 
  /// 使用自定义电池配置
  static Future<void> optimizationWithCustomBattery() async {
    try {
      print('执行自定义电池配置的优化...');

      final result = await ApiService.runOptimization(
        initialSoc: 0.5,
        batteryCapacity: 20.0, // 20 kWh
        batteryPower: 7.0, // 7 kW
        batteryEfficiency: 0.96, // 96%
      );

      if (result.isSuccess && result.optimization != null) {
        print('电池配置: ${result.batteryConfig?.capacityFormatted}');
        print('最大功率: ${result.batteryConfig?.powerFormatted}');
        _printOptimizationDetails(result.optimization!);
      }
    } catch (e) {
      print('优化出错: $e');
    }
  }

  /// 示例 5: 获取优化配置
  /// 
  /// 获取系统默认的电池和电价配置
  static Future<void> getConfiguration() async {
    try {
      print('获取优化配置...');

      final config = await ApiService.getOptimizationConfig();

      if (config['success'] == true) {
        final batteryConfig = config['config'];
        final priceSchedule = config['price_schedule'];

        print('电池配置:');
        print('  容量: ${batteryConfig['battery_capacity']} kWh');
        print('  功率: ${batteryConfig['max_power']} kW');
        print('  效率: ${(batteryConfig['efficiency'] * 100).toStringAsFixed(0)}%');

        print('\n电价配置:');
        print('  谷时: ${priceSchedule['valley']} 元/kWh (${priceSchedule['valley_hours']})');
        print('  平时: ${priceSchedule['normal']} 元/kWh (${priceSchedule['normal_hours']})');
        print('  峰时: ${priceSchedule['peak']} 元/kWh (${priceSchedule['peak_hours']})');
      }
    } catch (e) {
      print('获取配置出错: $e');
    }
  }

  /// 示例 6: 场景模拟对比
  /// 
  /// 对比不同电池配置的效果
  static Future<void> compareScenarios() async {
    try {
      print('执行场景对比...');

      final scenarios = [
        {'name': '无电池', 'capacity': 0, 'power': 0},
        {'name': '小型电池 (10kWh)', 'capacity': 10, 'power': 3},
        {'name': 'Tesla Powerwall (13.5kWh)', 'capacity': 13.5, 'power': 5},
        {'name': '大型电池 (20kWh)', 'capacity': 20, 'power': 7},
      ];

      final result = await ApiService.simulateScenarios(
        scenarios: scenarios,
      );

      if (result['success'] == true) {
        print('\n场景对比结果:');
        final comparison = result['comparison'] as List;
        
        for (var item in comparison) {
          print('\n${item['scenario']}:');
          print('  成本: ${item['cost']} 元');
          print('  节省: ${item['savings']} 元 (${item['savings_percent']}%)');
        }

        final best = result['best_scenario'];
        print('\n最佳方案: ${best['name']}');
        print('最大节省: ${best['savings']} 元');
      }
    } catch (e) {
      print('场景对比出错: $e');
    }
  }

  /// 示例 7: 分析优化结果详情
  /// 
  /// 详细分析每小时的调度计划
  static Future<void> analyzeOptimizationDetails() async {
    try {
      final result = await ApiService.runOptimization(initialSoc: 0.5);

      if (result.isSuccess && result.optimization != null) {
        final opt = result.optimization!;

        print('\n详细调度计划:');
        print('=' * 80);
        print('时间\t负载\t电价\t电池动作\tSOC\t状态');
        print('-' * 80);

        for (var point in opt.chartData) {
          print(
            '${point.hour.toString().padLeft(2, '0')}:00\t'
            '${point.load.toStringAsFixed(1)}\t'
            '${point.price.toStringAsFixed(1)}\t'
            '${point.batteryAction.toStringAsFixed(1)}\t'
            '${point.soc.toStringAsFixed(0)}%\t'
            '${point.batteryStatus} (${point.priceLabel})',
          );
        }

        print('=' * 80);
      }
    } catch (e) {
      print('分析出错: $e');
    }
  }

  /// 辅助方法: 打印优化详情
  static void _printOptimizationDetails(OptimizationData opt) {
    print('\n优化结果详情:');
    print('─' * 60);
    
    // 成本信息
    print('💰 成本分析:');
    print('  无电池成本: ${opt.summary.totalCostWithoutBattery.toStringAsFixed(2)} 元');
    print('  有电池成本: ${opt.summary.totalCostWithBattery.toStringAsFixed(2)} 元');
    print('  节省金额: ${opt.summary.savingsFormatted}');
    print('  节省比例: ${opt.summary.savingsPercentFormatted}');

    // 负载信息
    print('\n📊 负载统计:');
    print('  平均负载: ${opt.summary.avgLoad.toStringAsFixed(2)} kW');
    print('  峰值负载: ${opt.summary.peakLoad.toStringAsFixed(2)} kW');
    print('  谷值负载: ${opt.summary.minLoad.toStringAsFixed(2)} kW');
    print('  总负载: ${opt.summary.totalLoad.toStringAsFixed(2)} kWh');

    // 电池信息
    print('\n🔋 电池使用:');
    print('  总充电量: ${opt.summary.totalCharged.toStringAsFixed(2)} kWh');
    print('  总放电量: ${opt.summary.totalDischarged.toStringAsFixed(2)} kWh');
    print('  循环效率: ${opt.summary.cycleEfficiency.toStringAsFixed(1)}%');

    // 策略信息
    print('\n⚡ 调度策略:');
    print('  充电时段: ${opt.strategy.chargingHoursFormatted}');
    print('  放电时段: ${opt.strategy.dischargingHoursFormatted}');
    print('  充电次数: ${opt.strategy.chargingCount} 小时');
    print('  放电次数: ${opt.strategy.dischargingCount} 小时');

    print('─' * 60);
  }
}

/// 运行所有示例
Future<void> runAllExamples() async {
  print('\n🚀 开始运行优化服务示例...\n');

  // 示例 1: 基础优化
  print('\n【示例 1】基础优化');
  await OptimizationServiceExample.basicOptimization();
  await Future.delayed(const Duration(seconds: 1));

  // 示例 5: 获取配置
  print('\n【示例 5】获取配置');
  await OptimizationServiceExample.getConfiguration();

  print('\n✅ 示例运行完成！');
  print('\n💡 提示:');
  print('  - 其他示例需要用户认证，请在应用中使用');
  print('  - 查看代码了解更多使用方法');
}
