package org.xzq.aether.application.dto.project;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 更新项目请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateProjectRequest {

    @Size(max = 255, message = "项目名称不能超过 255 个字符")
    private String name;

    @Size(max = 5000, message = "项目描述不能超过 5000 个字符")
    private String description;
}
