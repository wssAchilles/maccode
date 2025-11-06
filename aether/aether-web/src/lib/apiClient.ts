import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { auth } from '@/lib/firebase';

/**
 * 创建 Axios 实例，配置基础 URL
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器
 * 自动将 Firebase ID Token 附加到每个请求的 Authorization 头
 * 
 * 根据 blueprint.md 阶段 7.2.1 的要求：
 * 1. 检查当前是否有登录用户
 * 2. 如果有，获取 Firebase ID Token
 * 3. 将 Token 以 Bearer 格式附加到请求头
 */
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      // 获取当前登录用户
      const user = auth.currentUser;
      
      if (user) {
        // 获取 Firebase ID Token
        const token = await user.getIdToken();
        
        // 附加到 Authorization 头
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('获取 Firebase Token 失败:', error);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 * 处理全局错误（如 401 未认证）
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('认证失败，Token 可能已过期');
      // 可以在这里触发登出或刷新 Token
    }
    return Promise.reject(error);
  }
);

export default apiClient;
