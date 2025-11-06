package org.xzq.aether.application.dto.card;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 指派用户到卡片请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AssignUserRequest {

    @NotBlank(message = "用户UID不能为空")
    private String userUid;
}
