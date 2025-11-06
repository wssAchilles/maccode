package org.xzq.aether.infrastructure.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * WebSocket 配置
 * 职责: 配置基于 STOMP 的 WebSocket 消息代理
 * 
 * 架构原则:
 * 1. /topic - 用于广播消息（如看板变更通知）
 * 2. /app - 用于应用目标前缀
 * 3. 支持 SockJS 回退机制
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    /**
     * 配置消息代理
     * - 启用基于内存的简单消息代理，目标前缀为 /topic
     * - 设置应用目标前缀为 /app
     */
    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // 启用简单的内存消息代理，用于广播消息
        // 客户端订阅 /topic/board/{boardId} 时，会从此代理接收消息
        registry.enableSimpleBroker("/topic");
        
        // 设置应用目标前缀
        // 客户端发送消息到 /app/... 时，会路由到对应的 @MessageMapping 方法
        registry.setApplicationDestinationPrefixes("/app");
    }

    /**
     * 注册 STOMP 端点
     * - 端点路径: /ws
     * - 允许的源: http://localhost:3000 (Next.js 前端)
     * - 启用 SockJS 回退支持
     */
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOrigins("http://localhost:3000", "http://localhost:3001")
                .withSockJS(); // 启用 SockJS 回退机制，兼容不支持 WebSocket 的浏览器
    }
}
