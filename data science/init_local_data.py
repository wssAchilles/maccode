import gridstatus
import pandas as pd
import numpy as np

# 配置
DAYS_BACK = 30
FILENAME = "cleaned_energy_data_all.csv"

def generate_initial_data():
    print(f"正在下载 CAISO (加州) 过去 {DAYS_BACK} 天的电力数据...")
    
    # 🌟 修改点 1: 将 PJM 替换为 CAISO
    iso = gridstatus.CAISO() 
    
    # 获取历史负载
    df_load = iso.get_load(start=pd.Timestamp.now() - pd.Timedelta(days=DAYS_BACK), end="today")
    
    print("正在处理数据格式...")
    # 重采样为每小时数据
    # CAISO 数据通常是 5分钟间隔，列名为 'Load'
    df_load['Time'] = pd.to_datetime(df_load['Time'])
    
    # 🌟 修改点 2: 确保时区处理 (CAISO 是太平洋时间，PJM 是东部时间)
    # 如果不需要严格时区，直接转为无时区处理即可
    df_load['Time'] = df_load['Time'].dt.tz_localize(None)
    
    df_hourly = df_load.set_index('Time').resample('h')['Load'].mean().reset_index()
    
    # 重命名列
    df_hourly.rename(columns={'Load': 'Site_Load', 'Time': 'Date'}, inplace=True)
    
    # 补充特征列
    df_hourly['Hour'] = df_hourly['Date'].dt.hour
    df_hourly['DayOfWeek'] = df_hourly['Date'].dt.dayofweek
    
    # 模拟历史温度 (注意：加州比费城暖和，稍微调高一点范围)
    df_hourly['Temperature'] = np.random.uniform(18, 30, size=len(df_hourly))
    
    # 模拟电价
    df_hourly['Price'] = df_hourly['Hour'].apply(lambda h: 0.6 if 8 <= h < 18 else 0.3)
    
    # 整理
    df_final = df_hourly[['Date', 'Hour', 'DayOfWeek', 'Temperature', 'Price', 'Site_Load']]
    df_final.dropna(inplace=True)
    
    df_final.to_csv(FILENAME, index=False)
    print(f"✅ CAISO 数据初始化成功！文件已生成: {FILENAME}")
    print(f"📊 数据行数: {len(df_final)}")

if __name__ == "__main__":
    generate_initial_data()