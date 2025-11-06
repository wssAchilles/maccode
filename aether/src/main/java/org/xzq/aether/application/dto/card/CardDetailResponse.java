package org.xzq.aether.application.dto.card;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * 卡片详情响应 DTO（包含完整信息）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CardDetailResponse {

    private Long id;
    private String title;
    private String description;
    private Double position;
    private Long listId;
    private String listName;
    private Long boardId;
    private String boardName;
    private Instant dueDate;
    private Instant createdAt;
    private Instant updatedAt;
    
    /**
     * 指派的用户列表
     */
    private List<CardAssigneeResponse> assignees;
}
