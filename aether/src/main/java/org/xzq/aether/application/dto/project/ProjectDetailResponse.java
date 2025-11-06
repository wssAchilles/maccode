package org.xzq.aether.application.dto.project;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * 项目详情响应 DTO（包含成员列表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProjectDetailResponse {

    private Long id;
    private String name;
    private String description;
    private String ownerUid;
    private String ownerUsername;
    private Instant createdAt;
    private Instant updatedAt;
    
    /**
     * 项目成员列表
     */
    private List<ProjectMemberResponse> members;
    
    /**
     * 看板数量
     */
    private Integer boardCount;
}
