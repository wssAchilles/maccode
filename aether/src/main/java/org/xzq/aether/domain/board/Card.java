package org.xzq.aether.domain.board;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.user.User;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * 卡片实体 - DDD 核心领域模型
 * 代表最小的任务单元
 */
@Entity
@Table(name = "cards")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Card {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    /**
     * 排序字段 - 使用 Double 以支持灵活的拖拽排序
     */
    @Column(nullable = false)
    private Double position;

    /**
     * 截止日期 (可选)
     */
    @Column
    private Instant dueDate;

    /**
     * 所属列表
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "list_id", nullable = false)
    private CardList list;

    /**
     * 指派的用户列表 (多对多)
     */
    @OneToMany(mappedBy = "id.card", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<CardAssignment> assignments = new ArrayList<>();

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建新卡片 (工厂方法)
     * @param title 卡片标题
     * @param position 排序位置
     * @param list 所属列表
     * @return 新卡片实例
     */
    public static Card create(String title, Double position, CardList list) {
        Card card = new Card();
        card.title = title;
        card.position = position;
        card.list = list;
        return card;
    }

    /**
     * 更新卡片内容
     * @param title 新标题
     * @param description 新描述
     * @param dueDate 新截止日期
     */
    public void update(String title, String description, Instant dueDate) {
        if (title != null && !title.isBlank()) {
            this.title = title;
        }
        if (description != null) {
            this.description = description;
        }
        this.dueDate = dueDate;
    }

    /**
     * 移动卡片到新列表
     * @param targetList 目标列表
     * @param newPosition 新位置
     */
    public void moveTo(CardList targetList, Double newPosition) {
        this.list = targetList;
        this.position = newPosition;
    }

    /**
     * 更新排序位置 (列表内移动)
     * @param newPosition 新位置
     */
    public void updatePosition(Double newPosition) {
        if (newPosition != null && newPosition >= 0) {
            this.position = newPosition;
        }
    }

    /**
     * 指派用户到卡片
     * @param user 用户
     */
    public void assignUser(User user) {
        CardAssignment assignment = CardAssignment.create(this, user);
        this.assignments.add(assignment);
    }

    /**
     * 移除用户指派
     * @param user 用户
     */
    public void unassignUser(User user) {
        this.assignments.removeIf(assignment -> 
            assignment.getId().getUser().getUid().equals(user.getUid())
        );
    }

    /**
     * 检查用户是否被指派到此卡片
     * @param userUid 用户 UID
     * @return true 如果已指派
     */
    public boolean isAssignedTo(String userUid) {
        return assignments.stream()
            .anyMatch(assignment -> assignment.getId().getUser().getUid().equals(userUid));
    }

    /**
     * 检查是否属于指定列表
     * @param listId 列表 ID
     * @return true 如果属于该列表
     */
    public boolean belongsToList(Long listId) {
        return this.list.getId().equals(listId);
    }
}
