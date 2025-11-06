package org.xzq.aether.domain.project;

import jakarta.persistence.Embeddable;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import lombok.AccessLevel;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.xzq.aether.domain.user.User;

import java.io.Serializable;

/**
 * ProjectMember 复合主键
 * 由 Project 和 User 共同组成
 */
@Embeddable
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@EqualsAndHashCode
public class ProjectMemberId implements Serializable {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_uid", nullable = false)
    private User user;

    /**
     * 创建复合主键
     * @param project 项目
     * @param user 用户
     */
    public ProjectMemberId(Project project, User user) {
        this.project = project;
        this.user = user;
    }
}
