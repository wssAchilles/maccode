package org.xzq.aether.domain.user;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.Instant;
import java.util.HashSet;
import java.util.Set;

/**
 * 用户领域实体 (User Domain Entity)
 * 职责: 存储从 Firebase 同步过来的用户信息
 * 
 * DDD 原则: 这是聚合根 (Aggregate Root)
 */
@Entity
@Table(name = "users")
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    /**
     * 主键: Firebase UID (不是自增ID)
     * 这是与 Firebase Authentication 的唯一关联点
     */
    @Id
    @Column(nullable = false, unique = true, length = 255)
    private String uid;

    /**
     * 用户邮箱 (唯一)
     */
    @Column(nullable = false, unique = true, length = 255)
    private String email;

    /**
     * 用户显示名称
     */
    @Column(nullable = false, length = 255)
    private String username;

    /**
     * 用户头像 URL
     */
    @Column(name = "avatar_url", length = 1024)
    private String avatarUrl;

    /**
     * 审计字段: 创建时间
     */
    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /**
     * 审计字段: 最后更新时间
     */
    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // ===== 领域关系 (Domain Relationships) =====

    /**
     * 关系: 我参与的项目成员关系
     */
    @OneToMany(mappedBy = "id.user", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private Set<org.xzq.aether.domain.project.ProjectMember> projectMemberships = new HashSet<>();

    /**
     * 关系: 我被指派的卡片
     */
    @OneToMany(mappedBy = "id.user", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private Set<org.xzq.aether.domain.board.CardAssignment> cardAssignments = new HashSet<>();

    /**
     * 关系: 我拥有的项目
     */
    @OneToMany(mappedBy = "owner", cascade = CascadeType.ALL)
    @Builder.Default
    private Set<org.xzq.aether.domain.project.Project> ownedProjects = new HashSet<>();

    /**
     * 关系: 我的活动日志
     */
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL)
    @Builder.Default
    private Set<org.xzq.aether.domain.activity.ActivityLog> activityLogs = new HashSet<>();

    // ===== 领域方法 (Domain Methods) - DDD 原则 =====

    /**
     * 更新用户信息 (从 Firebase 同步时使用)
     * 
     * @param email 新的邮箱
     * @param username 新的用户名
     * @param avatarUrl 新的头像 URL
     * @return 是否有更新
     */
    public boolean updateFromFirebase(String email, String username, String avatarUrl) {
        boolean hasChanges = false;

        if (email != null && !email.equals(this.email)) {
            this.email = email;
            hasChanges = true;
        }

        if (username != null && !username.equals(this.username)) {
            this.username = username;
            hasChanges = true;
        }

        if (avatarUrl != null && !avatarUrl.equals(this.avatarUrl)) {
            this.avatarUrl = avatarUrl;
            hasChanges = true;
        }

        return hasChanges;
    }

    /**
     * 检查用户是否是项目的成员
     * 
     * @param projectId 项目 ID
     * @return 是否是成员
     */
    public boolean isMemberOfProject(Long projectId) {
        return projectMemberships.stream()
                .anyMatch(pm -> pm.getId().getProject().getId().equals(projectId));
    }

    /**
     * 检查用户是否是项目的所有者
     * 
     * @param projectId 项目 ID
     * @return 是否是所有者
     */
    public boolean isOwnerOfProject(Long projectId) {
        return ownedProjects.stream()
                .anyMatch(p -> p.getId().equals(projectId));
    }
}
