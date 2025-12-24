/**
 * Firebase 配置文件
 * 
 * 使用单例模式确保 Firebase App 只初始化一次
 * 这在 Next.js 的热重载环境中尤为重要
 */

import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import { getFirestore, Firestore } from "firebase/firestore";

// Firebase 配置
// 使用环境变量，支持不同环境部署
const firebaseConfig = {
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "sentinel-ai-project-482208",
    // 以下配置为可选，Firestore 只需 projectId 即可工作
    // apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    // authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    // storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    // messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    // appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// 单例模式：检查是否已初始化
let app: FirebaseApp;
let db: Firestore;

if (getApps().length === 0) {
    // 首次初始化
    app = initializeApp(firebaseConfig);
    console.log("[Firebase] Initialized with project:", firebaseConfig.projectId);
} else {
    // 复用已有实例 (热重载时)
    app = getApp();
}

// 初始化 Firestore
db = getFirestore(app);

export { app, db };
