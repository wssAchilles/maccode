package org.xzq.aether.config;



import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import jakarta.annotation.PostConstruct;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;
import java.io.InputStream;

@Configuration
public class FirebaseConfig {

    @PostConstruct // 确保在应用启动时执行
    public void initialize() {
        try {
            // 1. 从 ClassPath (resources 目录) 读取密钥
            InputStream serviceAccount = new ClassPathResource("serviceAccountKey.json").getInputStream();

            // 2. 构建 Firebase 选项
            FirebaseOptions options = FirebaseOptions.builder()
                    .setCredentials(GoogleCredentials.fromStream(serviceAccount))
                    .build();

            // 3. 初始化 FirebaseApp（防止重复初始化）
            if (FirebaseApp.getApps().isEmpty()) {
                FirebaseApp.initializeApp(options);
                System.out.println("FirebaseApp initialized successfully.");
            }
        } catch (IOException e) {
            // 抛出运行时异常，如果初始化失败，应用应该启动失败
            throw new RuntimeException("Failed to initialize Firebase Admin SDK", e);
        }
    }
}