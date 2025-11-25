# 🚀 快速启动指南

## 本地测试

### 1. 测试数据采集 (推荐先测试这个)

```bash
cd back
python services/external_data_service.py
```

**预期输出**:

```
🔌 获取 CAISO 电力负载数据...
   ✓ CAISO 负载: 25000.00 MW
   ✓ 时间戳: 2024-11-24 08:00:00 (UTC)

🌤️  获取天气数据 (Los Angeles)...
   ✓ 温度: 25.5°C
   ✓ 时间戳: 2024-11-24 08:00:00 (UTC)

📝 开始 CSV 追加操作: data/processed/cleaned_energy_data_all.csv
   ✓ 追加新行，当前总行数: 1
   ✓ 上传到 Firebase Storage

✅ 数据采集任务完成!
```

### 2. 测试调度器

```bash
cd back
python scheduler.py
```

这会立即执行一次数据采集任务。

### 3. 测试模型训练 (可选，需要较长时间)

```bash
cd back
python -c "from services.ml_service import EnergyPredictor; p = EnergyPredictor(); p.train_model(use_firebase_storage=True)"
```

---

## 部署到 GAE

### 1. 确认配置

检查 `app.yaml` 中的环境变量:

```yaml
env_variables:
  STORAGE_BUCKET_NAME: "data-science-44398.firebasestorage.app"
  OPENWEATHER_API_KEY: "e8f11d28ce6faf3a9aa93828fb8fbff1"
  WEATHER_CITY_LAT: "34.05"
  WEATHER_CITY_LON: "-118.24"
```

### 2. 部署

```bash
cd back
gcloud app deploy app.yaml
```

### 3. 查看日志

```bash
gcloud app logs tail -s default
```

---

## 验证部署

### 1. 检查应用状态

```bash
curl https://YOUR-PROJECT-ID.appspot.com/health
```

### 2. 查看调度器日志

在日志中搜索:

- `✅ 数据管道调度器已启动`
- `⏰ 开始执行数据抓取任务`

### 3. 检查 Firebase Storage

访问 Firebase Console，确认文件已创建:

```
data/processed/cleaned_energy_data_all.csv
```

---

## 常见问题

### Q: 如何手动触发数据采集?

**方法 1**: 使用 Python 脚本

```python
from services.external_data_service import ExternalDataService
service = ExternalDataService()
service.fetch_and_publish()
```

**方法 2**: 使用调度器

```python
from scheduler import DataPipelineScheduler
scheduler = DataPipelineScheduler()
scheduler.run_now('fetch_data')
```

### Q: 如何查看当前 CSV 文件内容?

```python
from services.storage_service import StorageService
import pandas as pd

storage = StorageService()
temp_path = storage.download_to_temp('data/processed/cleaned_energy_data_all.csv')
df = pd.read_csv(temp_path)
print(df.tail(10))  # 查看最后 10 行
```

### Q: 调度器什么时候执行?

- **数据采集**: 每小时整点 (00:00, 01:00, 02:00, ...)
- **模型训练**: 每天凌晨 4:00 UTC (北京时间 12:00)

### Q: 如何停止调度器?

调度器会在应用停止时自动停止。如果需要手动停止:

```python
from scheduler import get_scheduler
scheduler = get_scheduler()
scheduler.stop()
```

---

## 下一步

1. ✅ 确认数据采集正常运行
2. ✅ 等待几小时，检查 CSV 文件是否持续更新
3. ✅ 等待第二天凌晨 4:00，检查模型是否自动重训
4. ✅ 监控 GAE 日志，确保没有错误

---

## 紧急联系

如果遇到问题，请检查:

1. GAE 日志: `gcloud app logs tail`
2. Firebase Storage 权限
3. API Key 配置
4. 网络连接

**祝部署顺利! 🎉**
