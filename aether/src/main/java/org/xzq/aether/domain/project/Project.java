package org.xzq.aether.domain.project;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.xzq.aether.domain.board.Board;
import org.xzq.aether.domain.user.User;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * 项目实体 - DDD 核心领域模型
 * 代表一个工作空间，是看板的容器
 */
@Entity
@Table(name = "projects")
@EntityListeners(AuditingEntityListener.class)
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Project {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    /**
     * 项目拥有者
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "owner_uid", nullable = false)
    private User owner;

    /**
     * 项目成员列表 (一对多)
     */
    @OneToMany(mappedBy = "id.project", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ProjectMember> members = new ArrayList<>();

    /**
     * 项目下的所有看板 (一对多)
     */
    @OneToMany(mappedBy = "project", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Board> boards = new ArrayList<>();

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    // ============ DDD 业务方法 ============

    /**
     * 创建新项目 (工厂方法)
     * @param name 项目名称
     * @param description 项目描述
     * @param owner 项目拥有者
     * @return 新项目实例
     */
    public static Project create(String name, String description, User owner) {
        Project project = new Project();
        project.name = name;
        project.description = description;
        project.owner = owner;
        return project;
    }

    /**
     * 更新项目信息
     * @param name 新名称
     * @param description 新描述
     */
    public void update(String name, String description) {
        if (name != null && !name.isBlank()) {
            this.name = name;
        }
        if (description != null) {
            this.description = description;
        }
    }

    /**
     * 添加项目成员
     * @param user 用户
     * @param role 角色
     */
    public void addMember(User user, ProjectRole role) {
        ProjectMember member = ProjectMember.create(this, user, role);
        this.members.add(member);
    }

    /**
     * 移除项目成员
     * @param user 用户
     */
    public void removeMember(User user) {
        this.members.removeIf(member -> 
            member.getId().getUser().getUid().equals(user.getUid())
        );
    }

    /**
     * 检查用户是否是项目成员
     * @param userUid 用户 UID
     * @return true 如果是成员
     */
    public boolean hasMember(String userUid) {
        return members.stream()
            .anyMatch(member -> member.getId().getUser().getUid().equals(userUid));
    }

    /**
     * 检查用户是否是项目拥有者
     * @param userUid 用户 UID
     * @return true 如果是拥有者
     */
    public boolean isOwner(String userUid) {
        return this.owner.getUid().equals(userUid);
    }

    /**
     * 添加看板
     * @param board 看板
     */
    public void addBoard(Board board) {
        this.boards.add(board);
    }
}
