package org.xzq.aether.infrastructure.websocket.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket 消息体
 * 职责: 统一的 WebSocket 推送消息格式
 * 
 * @param <T> 实际业务数据的类型
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class WebSocketMessage<T> {
    
    /**
     * 动作类型
     * 例如: CARD_MOVED, CARD_CREATED, CARD_UPDATED, CARD_DELETED, MEMBER_ADDED
     */
    private String actionType;
    
    /**
     * 实际业务数据
     */
    private T payload;
    
    /**
     * 时间戳
     */
    private Long timestamp;
    
    public static <T> WebSocketMessage<T> of(String actionType, T payload) {
        return new WebSocketMessage<>(actionType, payload, System.currentTimeMillis());
    }
}
