package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.user.User;

/**
 * 卡片删除事件
 * 职责: 表示"一张卡片被删除了"这一已发生的事实
 * 
 * 使用场景:
 * 1. WebSocket 广播 - 通知所有订阅该看板的客户端
 * 2. 活动日志 - 记录到 activity_logs 表
 */
@Getter
public class CardDeletedEvent extends DomainEvent {
    
    /**
     * 被删除的卡片ID和标题（因为实体已删除，保存关键信息）
     */
    private final Long cardId;
    private final String cardTitle;
    private final Long listId;
    private final Long boardId;
    
    public CardDeletedEvent(Long cardId, String cardTitle, Long listId, Long boardId, User triggeredBy) {
        super(triggeredBy);
        this.cardId = cardId;
        this.cardTitle = cardTitle;
        this.listId = listId;
        this.boardId = boardId;
    }
}
