package org.xzq.aether.application.dto.project;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 创建项目请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateProjectRequest {

    @NotBlank(message = "项目名称不能为空")
    @Size(max = 255, message = "项目名称不能超过 255 个字符")
    private String name;

    @Size(max = 5000, message = "项目描述不能超过 5000 个字符")
    private String description;
}
