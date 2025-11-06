package org.xzq.aether.application.dto.project;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.xzq.aether.domain.project.ProjectRole;

/**
 * 更新成员角色请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateMemberRoleRequest {

    @NotNull(message = "角色不能为空")
    private ProjectRole role;
}
