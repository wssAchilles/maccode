package org.xzq.aether.domain.board;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Card 仓储接口
 * 提供卡片的数据访问能力
 */
@Repository
public interface CardRepository extends JpaRepository<Card, Long> {

    /**
     * 查询列表下的所有卡片（按位置排序）
     * @param listId 列表 ID
     * @return 卡片列表
     */
    List<Card> findAllByListIdOrderByPositionAsc(Long listId);

    /**
     * 获取卡片详情（包含指派信息）
     * @param cardId 卡片 ID
     * @return 卡片（带指派）
     */
    @Query("SELECT c FROM Card c " +
           "LEFT JOIN FETCH c.assignments " +
           "WHERE c.id = :cardId")
    Optional<Card> findByIdWithAssignments(@Param("cardId") Long cardId);

    /**
     * 查询用户被指派的所有卡片
     * @param userUid 用户 UID
     * @return 卡片列表
     */
    @Query("SELECT c FROM Card c " +
           "JOIN c.assignments a " +
           "WHERE a.id.user.uid = :userUid")
    List<Card> findAllByAssigneeUid(@Param("userUid") String userUid);

    /**
     * 检查卡片是否属于指定列表
     * @param cardId 卡片 ID
     * @param listId 列表 ID
     * @return true 如果属于该列表
     */
    @Query("SELECT COUNT(c) > 0 FROM Card c " +
           "WHERE c.id = :cardId AND c.list.id = :listId")
    boolean existsByIdAndListId(
        @Param("cardId") Long cardId, 
        @Param("listId") Long listId
    );

    /**
     * 获取列表中的最大位置值
     * @param listId 列表 ID
     * @return 最大位置值
     */
    @Query("SELECT MAX(c.position) FROM Card c WHERE c.list.id = :listId")
    Optional<Double> findMaxPositionByListId(@Param("listId") Long listId);
}
