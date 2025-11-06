package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.user.User;

import java.time.Instant;

/**
 * 领域事件基类
 * 职责: 为所有领域事件提供通用属性
 * 
 * DDD 原则: 事件是对已发生事实的描述，使用过去式命名
 */
@Getter
public abstract class DomainEvent {
    
    /**
     * 事件发生时间
     */
    private final Instant occurredAt;
    
    /**
     * 触发事件的用户
     */
    private final User triggeredBy;
    
    protected DomainEvent(User triggeredBy) {
        this.occurredAt = Instant.now();
        this.triggeredBy = triggeredBy;
    }
}
