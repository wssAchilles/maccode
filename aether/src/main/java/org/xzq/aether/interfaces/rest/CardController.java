package org.xzq.aether.interfaces.rest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.xzq.aether.application.dto.card.*;
import org.xzq.aether.application.service.CardAppService;
import org.xzq.aether.domain.user.User;

import java.util.List;

/**
 * 卡片 REST Controller
 * 处理卡片相关的 HTTP 请求
 */
@RestController
@RequestMapping("/api/v1/cards")
@RequiredArgsConstructor
public class CardController {

    private final CardAppService cardAppService;

    /**
     * 创建新卡片
     * POST /api/v1/cards
     */
    @PostMapping
    public ResponseEntity<CardDetailResponse> createCard(
        @RequestParam Long listId,
        @Valid @RequestBody CreateCardRequest request,
        Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        CardDetailResponse response = cardAppService.createCard(listId, request, currentUser);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * 获取卡片详情
     * GET /api/v1/cards/{cardId}
     */
    @GetMapping("/{cardId}")
    public ResponseEntity<CardDetailResponse> getCardById(@PathVariable Long cardId) {
        CardDetailResponse response = cardAppService.getCardById(cardId);
        return ResponseEntity.ok(response);
    }

    /**
     * 更新卡片信息
     * PUT /api/v1/cards/{cardId}
     */
    @PutMapping("/{cardId}")
    public ResponseEntity<CardDetailResponse> updateCard(
        @PathVariable Long cardId,
        @Valid @RequestBody UpdateCardRequest request,
        Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        CardDetailResponse response = cardAppService.updateCard(cardId, request, currentUser);
        return ResponseEntity.ok(response);
    }

    /**
     * 删除卡片
     * DELETE /api/v1/cards/{cardId}
     */
    @DeleteMapping("/{cardId}")
    public ResponseEntity<Void> deleteCard(
        @PathVariable Long cardId,
        Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        cardAppService.deleteCard(cardId, currentUser);
        return ResponseEntity.noContent().build();
    }

    /**
     * 移动卡片（拖拽）
     * PATCH /api/v1/cards/{cardId}/move
     * 
     * 支持两种场景：
     * 1. 同一列表内移动：只改变 position
     * 2. 跨列表移动：改变 listId 和 position
     */
    @PatchMapping("/{cardId}/move")
    public ResponseEntity<CardDetailResponse> moveCard(
        @PathVariable Long cardId,
        @Valid @RequestBody MoveCardRequest request,
        Authentication authentication
    ) {
        User currentUser = (User) authentication.getPrincipal();
        CardDetailResponse response = cardAppService.moveCard(cardId, request, currentUser);
        return ResponseEntity.ok(response);
    }

    /**
     * 分配用户到卡片
     * POST /api/v1/cards/{cardId}/assignees
     */
    @PostMapping("/{cardId}/assignees")
    public ResponseEntity<CardDetailResponse> assignUser(
        @PathVariable Long cardId,
        @Valid @RequestBody AssignUserRequest request
    ) {
        CardDetailResponse response = cardAppService.assignUser(cardId, request);
        return ResponseEntity.ok(response);
    }

    /**
     * 取消分配用户
     * DELETE /api/v1/cards/{cardId}/assignees/{userUid}
     */
    @DeleteMapping("/{cardId}/assignees/{userUid}")
    public ResponseEntity<CardDetailResponse> unassignUser(
        @PathVariable Long cardId,
        @PathVariable String userUid
    ) {
        CardDetailResponse response = cardAppService.unassignUser(cardId, userUid);
        return ResponseEntity.ok(response);
    }

    /**
     * 获取我分配到的卡片
     * GET /api/v1/cards/my-assigned
     */
    @GetMapping("/my-assigned")
    public ResponseEntity<List<CardResponse>> getMyAssignedCards(Authentication authentication) {
        User currentUser = (User) authentication.getPrincipal();
        List<CardResponse> cards = cardAppService.getMyAssignedCards(currentUser);
        return ResponseEntity.ok(cards);
    }
}
