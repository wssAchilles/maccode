package org.xzq.aether.domain.board;

import jakarta.persistence.Embeddable;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import lombok.AccessLevel;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.xzq.aether.domain.user.User;

import java.io.Serializable;

/**
 * CardAssignment 复合主键
 * 由 Card 和 User 共同组成
 */
@Embeddable
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@EqualsAndHashCode
public class CardAssignmentId implements Serializable {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "card_id", nullable = false)
    private Card card;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_uid", nullable = false)
    private User user;

    /**
     * 创建复合主键
     * @param card 卡片
     * @param user 用户
     */
    public CardAssignmentId(Card card, User user) {
        this.card = card;
        this.user = user;
    }
}
