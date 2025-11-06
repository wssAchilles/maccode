package org.xzq.aether.domain.activity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.project.Project;
import org.xzq.aether.domain.user.User;

import java.time.Instant;

/**
 * 活动日志实体 - DDD 核心领域模型
 * 记录项目中的所有活动（谁在何时做了什么）
 */
@Entity
@Table(name = "activity_logs")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ActivityLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 活动描述消息
     * 例如："Achilles 将卡片 'X' 移动到了 '已完成'"
     */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String message;

    /**
     * 所属项目
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    /**
     * 操作者
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_uid", nullable = false)
    private User user;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建活动日志 (工厂方法)
     * @param message 活动描述
     * @param project 所属项目
     * @param user 操作者
     * @return 活动日志实例
     */
    public static ActivityLog create(String message, Project project, User user) {
        ActivityLog log = new ActivityLog();
        log.message = message;
        log.project = project;
        log.user = user;
        return log;
    }
}
