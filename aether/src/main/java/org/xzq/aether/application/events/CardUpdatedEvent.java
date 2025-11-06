package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.user.User;

/**
 * 卡片更新事件
 * 职责: 表示"一张卡片的信息被更新了"这一已发生的事实
 * 
 * 使用场景:
 * 1. WebSocket 广播 - 通知所有订阅该看板的客户端
 * 2. 活动日志 - 记录到 activity_logs 表
 */
@Getter
public class CardUpdatedEvent extends DomainEvent {
    
    /**
     * 被更新的卡片
     */
    private final Card card;
    
    public CardUpdatedEvent(Card card, User triggeredBy) {
        super(triggeredBy);
        this.card = card;
    }
}
