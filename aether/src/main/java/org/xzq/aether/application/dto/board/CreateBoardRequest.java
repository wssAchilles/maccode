package org.xzq.aether.application.dto.board;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 创建看板请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateBoardRequest {

    @NotBlank(message = "看板名称不能为空")
    @Size(max = 255, message = "看板名称不能超过 255 个字符")
    private String name;
}
