package org.xzq.aether.application.dto.board;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.xzq.aether.application.dto.card.CardResponse;

import java.util.List;

/**
 * 卡片列表响应 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CardListResponse {

    private Long id;
    private String name;
    private Double position;
    private Long boardId;
    
    /**
     * 列表下的所有卡片（已排序）
     */
    private List<CardResponse> cards;
}
