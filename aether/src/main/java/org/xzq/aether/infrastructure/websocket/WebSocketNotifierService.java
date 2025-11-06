package org.xzq.aether.infrastructure.websocket;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.xzq.aether.application.dto.card.CardDetailResponse;
import org.xzq.aether.application.events.*;
import org.xzq.aether.application.service.mapper.DtoMapper;
import org.xzq.aether.infrastructure.websocket.dto.WebSocketMessage;

/**
 * WebSocket 通知服务
 * 职责: 监听领域事件并通过 WebSocket 广播给订阅的客户端
 * 
 * [关键] 所有方法必须使用 @Async 异步执行，不阻塞主业务流程
 * 
 * 广播规则:
 * - 卡片事件: /topic/board/{boardId}
 * - 项目事件: /topic/project/{projectId}
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class WebSocketNotifierService {

    private final SimpMessagingTemplate messagingTemplate;
    private final DtoMapper dtoMapper;

    /**
     * 处理卡片移动事件
     * 广播到看板主题: /topic/board/{boardId}
     */
    @EventListener
    @Async
    public void handleCardMoved(CardMovedEvent event) {
        try {
            Long boardId = event.getCard().getList().getBoard().getId();
            String destination = "/topic/board/" + boardId;
            
            // 构造消息体
            CardDetailResponse payload = dtoMapper.toCardDetailResponse(event.getCard());
            WebSocketMessage<CardDetailResponse> message = WebSocketMessage.of("CARD_MOVED", payload);
            
            // 广播到指定主题
            messagingTemplate.convertAndSend(destination, message);
            
            log.debug("WebSocket 广播: {} -> {}", destination, message.getActionType());
        } catch (Exception e) {
            log.error("广播卡片移动事件失败", e);
        }
    }

    /**
     * 处理卡片创建事件
     */
    @EventListener
    @Async
    public void handleCardCreated(CardCreatedEvent event) {
        try {
            Long boardId = event.getCard().getList().getBoard().getId();
            String destination = "/topic/board/" + boardId;
            
            CardDetailResponse payload = dtoMapper.toCardDetailResponse(event.getCard());
            WebSocketMessage<CardDetailResponse> message = WebSocketMessage.of("CARD_CREATED", payload);
            
            messagingTemplate.convertAndSend(destination, message);
            
            log.debug("WebSocket 广播: {} -> {}", destination, message.getActionType());
        } catch (Exception e) {
            log.error("广播卡片创建事件失败", e);
        }
    }

    /**
     * 处理卡片更新事件
     */
    @EventListener
    @Async
    public void handleCardUpdated(CardUpdatedEvent event) {
        try {
            Long boardId = event.getCard().getList().getBoard().getId();
            String destination = "/topic/board/" + boardId;
            
            CardDetailResponse payload = dtoMapper.toCardDetailResponse(event.getCard());
            WebSocketMessage<CardDetailResponse> message = WebSocketMessage.of("CARD_UPDATED", payload);
            
            messagingTemplate.convertAndSend(destination, message);
            
            log.debug("WebSocket 广播: {} -> {}", destination, message.getActionType());
        } catch (Exception e) {
            log.error("广播卡片更新事件失败", e);
        }
    }

    /**
     * 处理卡片删除事件
     */
    @EventListener
    @Async
    public void handleCardDeleted(CardDeletedEvent event) {
        try {
            Long boardId = event.getBoardId();
            String destination = "/topic/board/" + boardId;
            
            // 删除事件的 payload 只包含必要信息
            var payload = new Object() {
                public final Long cardId = event.getCardId();
                public final String cardTitle = event.getCardTitle();
                public final Long listId = event.getListId();
            };
            
            WebSocketMessage<Object> message = WebSocketMessage.of("CARD_DELETED", payload);
            
            messagingTemplate.convertAndSend(destination, message);
            
            log.debug("WebSocket 广播: {} -> {}", destination, message.getActionType());
        } catch (Exception e) {
            log.error("广播卡片删除事件失败", e);
        }
    }

    /**
     * 处理项目成员添加事件
     * 广播到项目主题: /topic/project/{projectId}
     */
    @EventListener
    @Async
    public void handleProjectMemberAdded(ProjectMemberAddedEvent event) {
        try {
            Long projectId = event.getMember().getId().getProject().getId();
            String destination = "/topic/project/" + projectId;
            
            var payload = dtoMapper.toProjectMemberResponse(event.getMember());
            WebSocketMessage<Object> message = WebSocketMessage.of("MEMBER_ADDED", payload);
            
            messagingTemplate.convertAndSend(destination, message);
            
            log.debug("WebSocket 广播: {} -> {}", destination, message.getActionType());
        } catch (Exception e) {
            log.error("广播成员添加事件失败", e);
        }
    }
}
