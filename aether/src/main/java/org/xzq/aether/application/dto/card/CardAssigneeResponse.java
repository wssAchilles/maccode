package org.xzq.aether.application.dto.card;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 卡片指派人响应 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CardAssigneeResponse {

    private String userUid;
    private String username;
    private String email;
    private String avatarUrl;
    private Instant assignedAt;
}
