package org.xzq.aether.application.dto.board;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 更新看板请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateBoardRequest {

    @Size(max = 255, message = "看板名称不能超过 255 个字符")
    private String name;
}
