package org.xzq.aether.application.dto.board;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 看板响应 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BoardResponse {

    private Long id;
    private String name;
    private Long projectId;
    private Instant createdAt;
    
    /**
     * 列表数量
     */
    private Integer listCount;
    
    /**
     * 卡片总数
     */
    private Integer cardCount;
}
