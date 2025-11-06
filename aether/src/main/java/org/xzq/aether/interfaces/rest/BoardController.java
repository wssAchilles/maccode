package org.xzq.aether.interfaces.rest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.xzq.aether.application.dto.board.*;
import org.xzq.aether.application.service.BoardAppService;

import java.util.List;

/**
 * Board REST Controller
 * 处理看板和列表相关的 HTTP 请求
 */
@RestController
@RequestMapping("/api/v1/boards")
@RequiredArgsConstructor
public class BoardController {

    private final BoardAppService boardAppService;

    /**
     * 创建新看板
     * POST /api/v1/boards
     */
    @PostMapping
    public ResponseEntity<BoardResponse> createBoard(
        @RequestParam Long projectId,
        @Valid @RequestBody CreateBoardRequest request
    ) {
        BoardResponse response = boardAppService.createBoard(projectId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * 获取看板详情（包含所有列表和卡片）
     * GET /api/v1/boards/{boardId}
     */
    @GetMapping("/{boardId}")
    public ResponseEntity<BoardDetailResponse> getBoardDetails(@PathVariable Long boardId) {
        BoardDetailResponse response = boardAppService.getBoardDetails(boardId);
        return ResponseEntity.ok(response);
    }

    /**
     * 更新看板信息
     * PUT /api/v1/boards/{boardId}
     */
    @PutMapping("/{boardId}")
    public ResponseEntity<BoardResponse> updateBoard(
        @PathVariable Long boardId,
        @Valid @RequestBody UpdateBoardRequest request
    ) {
        BoardResponse response = boardAppService.updateBoard(boardId, request);
        return ResponseEntity.ok(response);
    }

    /**
     * 删除看板
     * DELETE /api/v1/boards/{boardId}
     */
    @DeleteMapping("/{boardId}")
    public ResponseEntity<Void> deleteBoard(@PathVariable Long boardId) {
        boardAppService.deleteBoard(boardId);
        return ResponseEntity.noContent().build();
    }

    /**
     * 创建列表
     * POST /api/v1/boards/{boardId}/lists
     */
    @PostMapping("/{boardId}/lists")
    public ResponseEntity<CardListResponse> createCardList(
        @PathVariable Long boardId,
        @Valid @RequestBody CreateCardListRequest request
    ) {
        CardListResponse response = boardAppService.createCardList(boardId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * 更新列表信息
     * PUT /api/v1/lists/{listId}
     */
    @PutMapping("/lists/{listId}")
    public ResponseEntity<CardListResponse> updateCardList(
        @PathVariable Long listId,
        @Valid @RequestBody UpdateCardListRequest request
    ) {
        CardListResponse response = boardAppService.updateCardList(listId, request);
        return ResponseEntity.ok(response);
    }

    /**
     * 删除列表
     * DELETE /api/v1/lists/{listId}
     */
    @DeleteMapping("/lists/{listId}")
    public ResponseEntity<Void> deleteCardList(@PathVariable Long listId) {
        boardAppService.deleteCardList(listId);
        return ResponseEntity.noContent().build();
    }

    /**
     * 批量更新列表顺序（拖拽排序）
     * PATCH /api/v1/boards/{boardId}/lists/order
     */
    @PatchMapping("/{boardId}/lists/order")
    public ResponseEntity<List<CardListResponse>> updateListOrder(
        @PathVariable Long boardId,
        @Valid @RequestBody UpdateListOrderRequest request
    ) {
        List<CardListResponse> response = boardAppService.updateListOrder(boardId, request);
        return ResponseEntity.ok(response);
    }
}
