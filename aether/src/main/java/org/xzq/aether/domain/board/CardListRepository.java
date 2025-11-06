package org.xzq.aether.domain.board;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * CardList 仓储接口
 * 提供卡片列表的数据访问能力
 */
@Repository
public interface CardListRepository extends JpaRepository<CardList, Long> {

    /**
     * 查询看板下的所有列表（按位置排序）
     * @param boardId 看板 ID
     * @return 列表列表
     */
    List<CardList> findAllByBoardIdOrderByPositionAsc(Long boardId);

    /**
     * 获取列表详情（包含卡片）
     * @param listId 列表 ID
     * @return 列表（带卡片）
     */
    @Query("SELECT l FROM CardList l " +
           "LEFT JOIN FETCH l.cards " +
           "WHERE l.id = :listId")
    Optional<CardList> findByIdWithCards(@Param("listId") Long listId);

    /**
     * 检查列表是否属于指定看板
     * @param listId 列表 ID
     * @param boardId 看板 ID
     * @return true 如果属于该看板
     */
    @Query("SELECT COUNT(l) > 0 FROM CardList l " +
           "WHERE l.id = :listId AND l.board.id = :boardId")
    boolean existsByIdAndBoardId(
        @Param("listId") Long listId, 
        @Param("boardId") Long boardId
    );

    /**
     * 获取看板中的最大位置值
     * @param boardId 看板 ID
     * @return 最大位置值
     */
    @Query("SELECT MAX(l.position) FROM CardList l WHERE l.board.id = :boardId")
    Optional<Double> findMaxPositionByBoardId(@Param("boardId") Long boardId);
}
