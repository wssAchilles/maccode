package org.xzq.aether.application.dto.project;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.xzq.aether.domain.project.ProjectRole;

import java.time.Instant;

/**
 * 项目成员响应 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProjectMemberResponse {

    private String userUid;
    private String username;
    private String email;
    private String avatarUrl;
    private ProjectRole role;
    private Instant joinedAt;
}
