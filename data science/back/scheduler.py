"""
定时任务调度器
Scheduler for Periodic Tasks

使用 APScheduler 实现:
1. 每小时抓取 CAISO 和天气数据
2. 每天凌晨重训模型

增强功能:
- 任务执行监控和记录
- 执行超时保护
- 错误重试机制
"""

import os
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.control_task_service import ControlTaskService
from services.operation_service import OperationService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DataPipelineScheduler:
    """数据管道调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler = BackgroundScheduler(
            timezone='UTC',  # 使用 UTC 时区
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 每个任务最多同时运行 1 个实例
                'misfire_grace_time': 300  # 错过任务的宽限时间 (秒)
            }
        )
        
        logger.info("✓ DataPipelineScheduler 初始化完成")
    
    def fetch_data_job(self):
        """
        数据抓取任务 (每小时执行)
        
        执行内容:
        - 获取 CAISO 电力负载
        - 获取 OpenWeather 天气数据
        - 追加到 Firebase Storage CSV
        - 记录执行状态到 Firestore
        """
        logger.info("="*80)
        logger.info("⏰ 开始执行数据抓取任务")
        logger.info("="*80)
        
        control_task = ControlTaskService.ensure_control_task(
            control_task_id='fetch_data_hourly',
            kind='scheduler',
            operation_type='fetch_data',
            title='Hourly data fetching from CAISO and OpenWeather',
            schedule='every 1 hours',
            default_input={'task_name': 'fetch_data'},
        )
        operation = OperationService.create_operation(
            'system',
            'fetch_data',
            {
                'task_name': 'fetch_data',
                'trigger': 'cron',
                'scheduled_time': datetime.utcnow().isoformat(),
            },
            control_task_id=control_task['id'],
            trigger='schedule',
        )
        operation_id = operation['job_id']

        OperationService.execute_operation(operation_id)
        
        logger.info("="*80 + "\n")
    
    def train_model_job(self):
        """
        模型训练任务 (每天执行)
        
        执行内容:
        - 从 Firebase Storage 下载最新数据
        - 重新训练随机森林模型
        - 保存模型到 Firebase Storage
        - 记录执行状态和模型指标
        """
        logger.info("="*80)
        logger.info("⏰ 开始执行模型训练任务")
        logger.info("="*80)
        
        control_task = ControlTaskService.ensure_control_task(
            control_task_id='train_model_daily',
            kind='scheduler',
            operation_type='train_model',
            title='Daily forecast model retraining',
            schedule='every day 04:00 UTC',
            default_input={'task_name': 'train_model', 'n_estimators': 100},
        )
        operation = OperationService.create_operation(
            'system',
            'train_model',
            {
                'task_name': 'train_model',
                'trigger': 'cron',
                'scheduled_time': datetime.utcnow().isoformat(),
                'n_estimators': 100,
                'use_firebase_storage': True,
            },
            control_task_id=control_task['id'],
            trigger='schedule',
        )
        operation_id = operation['job_id']
        
        OperationService.execute_operation(operation_id)
        
        logger.info("="*80 + "\n")
    
    def start(self):
        """
        启动调度器
        
        配置任务:
        - 数据抓取: 每小时执行一次 (整点)
        - 模型训练: 每天凌晨 4:00 UTC 执行
        """
        logger.info("\n" + "="*80)
        logger.info("🚀 启动数据管道调度器")
        logger.info("="*80)
        
        # 检查是否在 GAE 环境中
        is_gae = os.getenv('GAE_ENV', '').startswith('standard')
        
        if is_gae:
            logger.info("📍 运行环境: Google App Engine")
        else:
            logger.info("📍 运行环境: 本地开发")
        
        # 1. 数据抓取任务 (每小时整点执行)
        self.scheduler.add_job(
            func=self.fetch_data_job,
            trigger=CronTrigger(minute=0, timezone='UTC'),  # 每小时的第 0 分钟
            id='fetch_data_hourly',
            name='数据抓取任务 (每小时)',
            replace_existing=True
        )
        logger.info("✓ 已添加任务: 数据抓取 (每小时整点)")
        
        # 2. 模型训练任务 (每天凌晨 4:00 UTC 执行)
        self.scheduler.add_job(
            func=self.train_model_job,
            trigger=CronTrigger(hour=4, minute=0, timezone='UTC'),
            id='train_model_daily',
            name='模型训练任务 (每天凌晨 4:00 UTC)',
            replace_existing=True
        )
        logger.info("✓ 已添加任务: 模型训练 (每天凌晨 4:00 UTC)")
        
        # 启动调度器
        self.scheduler.start()
        logger.info("✅ 调度器已启动")
        
        # 打印下次执行时间
        jobs = self.scheduler.get_jobs()
        logger.info(f"\n📋 已注册任务 ({len(jobs)} 个):")
        for job in jobs:
            next_run = job.next_run_time
            if next_run:
                logger.info(f"   - {job.name}")
                logger.info(f"     下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        logger.info("="*80 + "\n")
    
    def stop(self):
        """停止调度器"""
        logger.info("🛑 停止调度器...")
        self.scheduler.shutdown(wait=False)
        logger.info("✓ 调度器已停止")
    
    def run_now(self, job_name='fetch_data'):
        """
        立即执行指定任务 (用于测试)
        
        Args:
            job_name: 任务名称 ('fetch_data' 或 'train_model')
        """
        logger.info(f"\n🧪 手动触发任务: {job_name}")
        
        if job_name == 'fetch_data':
            self.fetch_data_job()
        elif job_name == 'train_model':
            self.train_model_job()
        else:
            logger.error(f"❌ 未知任务: {job_name}")


# 全局调度器实例
_scheduler_instance = None


def get_scheduler():
    """
    获取调度器单例
    
    Returns:
        DataPipelineScheduler: 调度器实例
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = DataPipelineScheduler()
    
    return _scheduler_instance


def init_scheduler():
    """
    初始化并启动调度器
    
    此函数应在 Flask 应用启动时调用
    注意: 在 GAE 多实例环境中，每个实例都会运行调度器
    """
    # 防止在 Flask 重载时重复启动
    # 防止在 Flask 重载时重复启动
    # WERKZEUG_RUN_MAIN 为 true 表示这是 Werkzeug 重载器生成的子进程（实际运行服务的进程）
    # 在 GAE 环境中，没有 Werkzeug重载器，所以直接检查是否是主程序
    if os.getenv('GAE_ENV', '').startswith('standard') or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = get_scheduler()
        if not scheduler.scheduler.running:
            scheduler.start()
        return scheduler
    else:
        # 本地开发的主进程（监控进程），不启动调度器，防止双重启动
        logger.info("⏸️  跳过调度器启动 (不论是 Flask 监控进程还是非运行状态)")
        return None


# 测试代码
if __name__ == "__main__":
    print("\n🧪 测试调度器\n")
    
    scheduler = DataPipelineScheduler()
    
    # 测试数据抓取
    print("【测试 1】立即执行数据抓取任务")
    scheduler.run_now('fetch_data')
    
    # 可选: 测试模型训练 (需要较长时间)
    # print("\n【测试 2】立即执行模型训练任务")
    # scheduler.run_now('train_model')
    
    print("\n✅ 测试完成!")
