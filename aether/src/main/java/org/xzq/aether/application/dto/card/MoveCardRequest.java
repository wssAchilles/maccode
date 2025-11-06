package org.xzq.aether.application.dto.card;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 移动卡片请求 DTO
 * 用于实现拖拽功能
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MoveCardRequest {

    /**
     * 目标列表 ID
     */
    @NotNull(message = "目标列表ID不能为空")
    private Long targetListId;

    /**
     * 新位置
     */
    @NotNull(message = "新位置不能为空")
    private Double newPosition;
}
