package org.xzq.aether.application.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.application.dto.card.*;
import org.xzq.aether.application.events.*;
import org.xzq.aether.application.service.mapper.DtoMapper;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.board.CardList;
import org.xzq.aether.domain.board.CardListRepository;
import org.xzq.aether.domain.board.CardRepository;
import org.xzq.aether.domain.user.User;
import org.xzq.aether.domain.user.UserRepository;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 卡片应用服务
 * 编排卡片相关的业务逻辑，包括复杂的拖拽移动逻辑
 * 
 * [Milestone 4] 集成事件驱动架构：
 * - 在核心业务完成后发布领域事件
 * - 事件会被异步监听器消费（WebSocket广播、活动日志）
 */
@Service
@RequiredArgsConstructor
@Transactional
@Slf4j
public class CardAppService {

    private final CardRepository cardRepository;
    private final CardListRepository cardListRepository;
    private final UserRepository userRepository;
    private final DtoMapper dtoMapper;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * 创建新卡片
     * 需要是卡片所属看板的成员
     * 
     * listId 从 URL 路径获取，卡片自动添加到列表末尾
     * [Milestone 4] 发布 CardCreatedEvent 事件
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, " +
                  "@cardListRepository.findById(#listId).get().getBoard().getId())")
    public CardDetailResponse createCard(Long listId, CreateCardRequest request, User currentUser) {
        log.info("在列表 {} 中创建卡片: {}", listId, request.getTitle());
        
        CardList cardList = cardListRepository.findById(listId)
            .orElseThrow(() -> new IllegalArgumentException("列表不存在: " + listId));
        
        // 获取下一个可用的位置
        Double nextPosition = cardRepository.findMaxPositionByListId(listId)
            .map(max -> max + 1.0)
            .orElse(1.0);
        
        // 创建卡片实体
        Card card = Card.create(request.getTitle(), nextPosition, cardList);
        card.update(request.getTitle(), request.getDescription(), request.getDueDate());
        card = cardRepository.save(card);
        
        log.info("卡片 {} 创建成功，ID: {}", card.getTitle(), card.getId());
        
        // [Milestone 4] 发布事件 - 解耦业务逻辑与通知/日志
        eventPublisher.publishEvent(new CardCreatedEvent(card, currentUser));
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 获取卡片详情
     * 需要是卡片所属看板的成员
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public CardDetailResponse getCardById(Long cardId) {
        log.debug("获取卡片详情: {}", cardId);
        
        Card card = cardRepository.findByIdWithAssignments(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 更新卡片内容
     * 需要是卡片所属看板的成员
     * [Milestone 4] 发布 CardUpdatedEvent 事件
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public CardDetailResponse updateCard(Long cardId, UpdateCardRequest request, User currentUser) {
        log.info("更新卡片 {}: {}", cardId, request);
        
        Card card = cardRepository.findById(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        // 调用领域模型的业务方法
        card.update(request.getTitle(), request.getDescription(), request.getDueDate());
        
        // [Milestone 4] 发布事件
        eventPublisher.publishEvent(new CardUpdatedEvent(card, currentUser));
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 删除卡片
     * 需要是卡片所属看板的成员
     * [Milestone 4] 发布 CardDeletedEvent 事件
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public void deleteCard(Long cardId, User currentUser) {
        log.warn("删除卡片: {}", cardId);
        
        Card card = cardRepository.findById(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        // 在删除前保存必要信息用于事件
        Long listId = card.getList().getId();
        Long boardId = card.getList().getBoard().getId();
        String title = card.getTitle();
        
        cardRepository.delete(card);
        
        log.info("卡片 {} 已删除", cardId);
        
        // [Milestone 4] 发布事件
        eventPublisher.publishEvent(new CardDeletedEvent(cardId, title, listId, boardId, currentUser));
    }

    /**
     * 移动卡片（核心拖拽逻辑）
     * 支持两种场景：
     * 1. 列表内移动：只更新卡片位置
     * 2. 跨列表移动：更新卡片的列表关联和位置
     * 
     * 需要是卡片所属看板的成员
     * [Milestone 4] 发布 CardMovedEvent 事件
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public CardDetailResponse moveCard(Long cardId, MoveCardRequest request, User currentUser) {
        log.info("移动卡片 {} 到列表 {}，位置 {}", 
            cardId, request.getTargetListId(), request.getNewPosition());
        
        Card card = cardRepository.findById(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        CardList targetList = cardListRepository.findById(request.getTargetListId())
            .orElseThrow(() -> new IllegalArgumentException("目标列表不存在: " + request.getTargetListId()));
        
        Long currentListId = card.getList().getId();
        Long targetListId = targetList.getId();
        
        if (currentListId.equals(targetListId)) {
            // 场景1：列表内移动
            log.debug("列表内移动卡片 {}", cardId);
            card.updatePosition(request.getNewPosition());
            
            // 更新受影响的其他卡片位置
            updateCardPositionsInList(currentListId, cardId, request.getNewPosition());
        } else {
            // 场景2：跨列表移动
            log.debug("跨列表移动卡片 {} 从 {} 到 {}", cardId, currentListId, targetListId);
            card.moveTo(targetList, request.getNewPosition());
            
            // 更新两个列表中受影响的卡片位置
            updateCardPositionsInList(currentListId, null, null);
            updateCardPositionsInList(targetListId, cardId, request.getNewPosition());
        }
        
        log.info("卡片 {} 移动完成", cardId);
        
        // [Milestone 4] 发布事件 - 通知所有订阅该看板的客户端
        eventPublisher.publishEvent(new CardMovedEvent(card, currentListId, targetListId, currentUser));
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 更新列表中的卡片位置（处理拖拽后的位置调整）
     * 
     * @param listId 列表 ID
     * @param movedCardId 被移动的卡片 ID（null 表示卡片被移出该列表）
     * @param newPosition 新位置（null 表示重新计算所有位置）
     */
    private void updateCardPositionsInList(Long listId, Long movedCardId, Double newPosition) {
        List<Card> cards = cardRepository.findAllByListIdOrderByPositionAsc(listId);
        
        if (newPosition == null || movedCardId == null) {
            // 重新计算所有卡片位置（用于卡片被移出列表时）
            for (int i = 0; i < cards.size(); i++) {
                cards.get(i).updatePosition((double) i);
            }
        } else {
            // 调整受影响卡片的位置
            for (Card card : cards) {
                if (card.getId().equals(movedCardId)) {
                    continue; // 跳过被移动的卡片（已在外部更新）
                }
                
                Double currentPos = card.getPosition();
                if (currentPos >= newPosition) {
                    // 位置大于等于新位置的卡片，位置 +1
                    card.updatePosition(currentPos + 1.0);
                }
            }
        }
    }

    /**
     * 指派用户到卡片
     * 需要是卡片所属看板的成员
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public CardDetailResponse assignUser(Long cardId, AssignUserRequest request) {
        log.info("指派用户 {} 到卡片 {}", request.getUserUid(), cardId);
        
        Card card = cardRepository.findByIdWithAssignments(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        User user = userRepository.findById(request.getUserUid())
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + request.getUserUid()));
        
        // 检查用户是否已被指派
        if (card.isAssignedTo(user.getUid())) {
            throw new IllegalStateException("用户已被指派到该卡片");
        }
        
        // 调用领域模型的业务方法
        card.assignUser(user);
        
        log.info("用户 {} 已指派到卡片 {}", user.getUid(), cardId);
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 移除用户指派
     * 需要是卡片所属看板的成员
     */
    @PreAuthorize("@permissionService.canEditCard(authentication, #cardId)")
    public CardDetailResponse unassignUser(Long cardId, String userUid) {
        log.info("从卡片 {} 移除用户 {}", cardId, userUid);
        
        Card card = cardRepository.findByIdWithAssignments(cardId)
            .orElseThrow(() -> new IllegalArgumentException("卡片不存在: " + cardId));
        
        User user = userRepository.findById(userUid)
            .orElseThrow(() -> new IllegalArgumentException("用户不存在: " + userUid));
        
        // 调用领域模型的业务方法
        card.unassignUser(user);
        
        log.info("用户 {} 已从卡片 {} 移除", userUid, cardId);
        
        return dtoMapper.toCardDetailResponse(card);
    }

    /**
     * 获取用户被指派的所有卡片
     */
    public List<CardResponse> getMyAssignedCards(User currentUser) {
        log.debug("获取用户 {} 的所有指派卡片", currentUser.getUid());
        
        List<Card> cards = cardRepository.findAllByAssigneeUid(currentUser.getUid());
        
        return cards.stream()
            .map(dtoMapper::toCardResponse)
            .collect(Collectors.toList());
    }
}
