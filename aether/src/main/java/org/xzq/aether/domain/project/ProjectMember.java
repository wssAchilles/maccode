package org.xzq.aether.domain.project;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.user.User;

import java.time.Instant;

/**
 * 项目成员实体
 * User 和 Project 的多对多关联表，附加角色信息
 */
@Entity
@Table(name = "project_members")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ProjectMember {

    @EmbeddedId
    private ProjectMemberId id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 50)
    private ProjectRole role;

    @CreatedDate
    @Column(name = "joined_at", nullable = false, updatable = false)
    private Instant joinedAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建项目成员 (工厂方法)
     * @param project 项目
     * @param user 用户
     * @param role 角色
     * @return 项目成员实例
     */
    public static ProjectMember create(Project project, User user, ProjectRole role) {
        ProjectMember member = new ProjectMember();
        member.id = new ProjectMemberId(project, user);
        member.role = role;
        return member;
    }

    /**
     * 更新角色
     * @param newRole 新角色
     */
    public void updateRole(ProjectRole newRole) {
        if (newRole != null) {
            this.role = newRole;
        }
    }

    /**
     * 检查是否是拥有者
     * @return true 如果是拥有者
     */
    public boolean isOwner() {
        return this.role == ProjectRole.OWNER;
    }

    /**
     * 检查是否是管理员或拥有者
     * @return true 如果是管理员或拥有者
     */
    public boolean isAdminOrOwner() {
        return this.role == ProjectRole.OWNER || this.role == ProjectRole.ADMIN;
    }
}
