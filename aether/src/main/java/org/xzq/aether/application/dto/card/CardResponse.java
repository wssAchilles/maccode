package org.xzq.aether.application.dto.card;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 卡片响应 DTO（简化版，用于列表显示）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CardResponse {

    private Long id;
    private String title;
    private Double position;
    private Long listId;
    private Instant dueDate;
    private Instant createdAt;
    private Instant updatedAt;
    
    /**
     * 指派人数
     */
    private Integer assigneeCount;
}
