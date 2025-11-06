package org.xzq.aether.application.dto.board;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 更新列表排序请求 DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateListOrderRequest {

    @NotNull(message = "列表ID顺序不能为空")
    private List<Long> listIds;
}
