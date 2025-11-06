package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.user.User;

/**
 * 卡片移动事件
 * 职责: 表示"一张卡片被移动了"这一已发生的事实
 * 
 * 使用场景:
 * 1. WebSocket 广播 - 通知所有订阅该看板的客户端
 * 2. 活动日志 - 记录到 activity_logs 表
 */
@Getter
public class CardMovedEvent extends DomainEvent {
    
    /**
     * 被移动的卡片
     */
    private final Card card;
    
    /**
     * 原列表 ID
     */
    private final Long oldListId;
    
    /**
     * 新列表 ID
     */
    private final Long newListId;
    
    public CardMovedEvent(Card card, Long oldListId, Long newListId, User triggeredBy) {
        super(triggeredBy);
        this.card = card;
        this.oldListId = oldListId;
        this.newListId = newListId;
    }
}
