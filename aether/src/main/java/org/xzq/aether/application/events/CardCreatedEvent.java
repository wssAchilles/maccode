package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.user.User;

/**
 * 卡片创建事件
 * 职责: 表示"一张新卡片被创建了"这一已发生的事实
 * 
 * 使用场景:
 * 1. WebSocket 广播 - 通知所有订阅该看板的客户端
 * 2. 活动日志 - 记录到 activity_logs 表
 */
@Getter
public class CardCreatedEvent extends DomainEvent {
    
    /**
     * 被创建的卡片
     */
    private final Card card;
    
    public CardCreatedEvent(Card card, User triggeredBy) {
        super(triggeredBy);
        this.card = card;
    }
}
