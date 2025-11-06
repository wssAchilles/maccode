package org.xzq.aether.application.dto.board;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * 看板详情响应 DTO（包含所有列表和卡片）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BoardDetailResponse {

    private Long id;
    private String name;
    private Long projectId;
    private Instant createdAt;
    
    /**
     * 看板下的所有列表（已排序）
     */
    private List<CardListResponse> lists;
}
