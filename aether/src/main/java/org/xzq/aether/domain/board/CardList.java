package org.xzq.aether.domain.board;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 卡片列表实体 - DDD 核心领域模型
 * 代表看板中的一个列表（如"待办"、"进行中"），是卡片的容器
 */
@Entity
@Table(name = "card_lists")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CardList {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    /**
     * 排序字段 - 使用 Double 以支持灵活的拖拽排序
     * 例如：在位置 1.0 和 2.0 之间插入，可以使用 1.5
     */
    @Column(nullable = false)
    private Double position;

    /**
     * 所属看板
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "board_id", nullable = false)
    private Board board;

    /**
     * 列表下的所有卡片 (一对多，按 position 排序)
     */
    @OneToMany(mappedBy = "list", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("position ASC")
    private List<Card> cards = new ArrayList<>();

    // ============ DDD 业务方法 ============

    /**
     * 创建新列表 (工厂方法)
     * @param name 列表名称
     * @param position 排序位置
     * @param board 所属看板
     * @return 新列表实例
     */
    public static CardList create(String name, Double position, Board board) {
        CardList cardList = new CardList();
        cardList.name = name;
        cardList.position = position;
        cardList.board = board;
        return cardList;
    }

    /**
     * 更新列表名称
     * @param name 新名称
     */
    public void updateName(String name) {
        if (name != null && !name.isBlank()) {
            this.name = name;
        }
    }

    /**
     * 更新排序位置
     * @param position 新位置
     */
    public void updatePosition(Double position) {
        if (position != null && position >= 0) {
            this.position = position;
        }
    }

    /**
     * 添加卡片
     * @param card 卡片
     */
    public void addCard(Card card) {
        this.cards.add(card);
    }

    /**
     * 检查是否属于指定看板
     * @param boardId 看板 ID
     * @return true 如果属于该看板
     */
    public boolean belongsToBoard(Long boardId) {
        return this.board.getId().equals(boardId);
    }

    /**
     * 获取下一个可用的卡片位置
     * @return 新卡片应该使用的位置
     */
    public Double getNextCardPosition() {
        if (cards.isEmpty()) {
            return 1.0;
        }
        return cards.get(cards.size() - 1).getPosition() + 1.0;
    }
}
