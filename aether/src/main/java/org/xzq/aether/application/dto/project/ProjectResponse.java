package org.xzq.aether.application.dto.project;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 项目响应 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProjectResponse {

    private Long id;
    private String name;
    private String description;
    private String ownerUid;
    private String ownerUsername;
    private Instant createdAt;
    private Instant updatedAt;
    
    /**
     * 成员数量
     */
    private Integer memberCount;
    
    /**
     * 看板数量
     */
    private Integer boardCount;
}
