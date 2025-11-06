package org.xzq.aether.application.dto.card;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 更新卡片请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateCardRequest {

    @Size(max = 255, message = "卡片标题不能超过 255 个字符")
    private String title;

    @Size(max = 5000, message = "卡片描述不能超过 5000 个字符")
    private String description;

    /**
     * 截止日期（可选，null 表示清除截止日期）
     */
    private Instant dueDate;
}
