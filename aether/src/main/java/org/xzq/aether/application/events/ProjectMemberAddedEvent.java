package org.xzq.aether.application.events;

import lombok.Getter;
import org.xzq.aether.domain.project.ProjectMember;
import org.xzq.aether.domain.user.User;

/**
 * 项目成员添加事件
 * 职责: 表示"一个新成员被添加到项目中"这一已发生的事实
 * 
 * 使用场景:
 * 1. WebSocket 广播 - 通知所有项目成员
 * 2. 活动日志 - 记录到 activity_logs 表
 * 3. (可选) 发送通知给新成员
 */
@Getter
public class ProjectMemberAddedEvent extends DomainEvent {
    
    /**
     * 新添加的项目成员
     */
    private final ProjectMember member;
    
    public ProjectMemberAddedEvent(ProjectMember member, User triggeredBy) {
        super(triggeredBy);
        this.member = member;
    }
}
