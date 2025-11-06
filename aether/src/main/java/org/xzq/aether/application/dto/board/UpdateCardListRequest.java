package org.xzq.aether.application.dto.board;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 更新卡片列表请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateCardListRequest {

    @Size(max = 255, message = "列表名称不能超过 255 个字符")
    private String name;
}
