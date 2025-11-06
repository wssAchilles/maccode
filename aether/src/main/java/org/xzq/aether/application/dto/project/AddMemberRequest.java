package org.xzq.aether.application.dto.project;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.xzq.aether.domain.project.ProjectRole;

/**
 * 添加项目成员请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AddMemberRequest {

    @NotBlank(message = "用户 UID 不能为空")
    private String userUid;

    @NotNull(message = "角色不能为空")
    private ProjectRole role;
}
