package org.xzq.aether.domain.board;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.user.User;

import java.time.Instant;

/**
 * 卡片指派实体
 * Card 和 User 的多对多关联表
 */
@Entity
@Table(name = "card_assignments")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CardAssignment {

    @EmbeddedId
    private CardAssignmentId id;

    @CreatedDate
    @Column(name = "assigned_at", nullable = false, updatable = false)
    private Instant assignedAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建卡片指派 (工厂方法)
     * @param card 卡片
     * @param user 用户
     * @return 卡片指派实例
     */
    public static CardAssignment create(Card card, User user) {
        CardAssignment assignment = new CardAssignment();
        assignment.id = new CardAssignmentId(card, user);
        return assignment;
    }
}
