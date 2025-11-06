package org.xzq.aether.application.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.xzq.aether.application.dto.board.*;
import org.xzq.aether.application.service.mapper.DtoMapper;
import org.xzq.aether.domain.board.Board;
import org.xzq.aether.domain.board.BoardRepository;
import org.xzq.aether.domain.board.CardList;
import org.xzq.aether.domain.board.CardListRepository;
import org.xzq.aether.domain.project.Project;
import org.xzq.aether.domain.project.ProjectRepository;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 看板应用服务
 * 编排看板相关的业务逻辑
 */
@Service
@RequiredArgsConstructor
@Transactional
@Slf4j
public class BoardAppService {

    private final BoardRepository boardRepository;
    private final CardListRepository cardListRepository;
    private final ProjectRepository projectRepository;
    private final DtoMapper dtoMapper;

    /**
     * 创建新看板
     * 需要是项目成员才能创建看板
     */
    @PreAuthorize("@permissionService.isProjectMember(authentication, #projectId)")
    public BoardResponse createBoard(Long projectId, CreateBoardRequest request) {
        log.info("在项目 {} 中创建看板: {}", projectId, request.getName());
        
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("项目不存在: " + projectId));
        
        // 创建看板实体
        Board board = Board.create(request.getName(), project);
        board = boardRepository.save(board);
        
        log.info("看板 {} 创建成功，ID: {}", board.getName(), board.getId());
        
        return dtoMapper.toBoardResponse(board);
    }

    /**
     * 获取看板详情（包含所有列表和卡片）
     * 需要是看板所属项目的成员
     * 
     * 注意：使用 JOIN FETCH 避免 N+1 查询问题
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, #boardId)")
    public BoardDetailResponse getBoardDetails(Long boardId) {
        log.debug("获取看板详情: {}", boardId);
        
        Board board = boardRepository.findByIdWithListsAndCards(boardId)
            .orElseThrow(() -> new IllegalArgumentException("看板不存在: " + boardId));
        
        return dtoMapper.toBoardDetailResponse(board);
    }

    /**
     * 更新看板信息
     * 需要是看板所属项目的成员
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, #boardId)")
    public BoardResponse updateBoard(Long boardId, UpdateBoardRequest request) {
        log.info("更新看板 {}: {}", boardId, request);
        
        Board board = boardRepository.findById(boardId)
            .orElseThrow(() -> new IllegalArgumentException("看板不存在: " + boardId));
        
        // 调用领域模型的业务方法
        board.updateName(request.getName());
        
        return dtoMapper.toBoardResponse(board);
    }

    /**
     * 删除看板
     * 需要是看板所属项目的管理员或拥有者
     */
    @PreAuthorize("@permissionService.isProjectAdminOrOwner(authentication, " +
                  "@boardRepository.findById(#boardId).get().getProject().getId())")
    public void deleteBoard(Long boardId) {
        log.warn("删除看板: {}", boardId);
        
        Board board = boardRepository.findById(boardId)
            .orElseThrow(() -> new IllegalArgumentException("看板不存在: " + boardId));
        
        boardRepository.delete(board);
        
        log.info("看板 {} 已删除", boardId);
    }

    /**
     * 获取项目下的所有看板
     * 需要是项目成员才能访问
     */
    @PreAuthorize("@permissionService.isProjectMember(authentication, #projectId)")
    public List<BoardResponse> getProjectBoards(Long projectId) {
        log.debug("获取项目 {} 的所有看板", projectId);
        
        List<Board> boards = boardRepository.findAllByProjectId(projectId);
        
        return boards.stream()
            .map(dtoMapper::toBoardResponse)
            .collect(Collectors.toList());
    }

    /**
     * 创建卡片列表
     * 需要是看板所属项目的成员
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, #boardId)")
    public CardListResponse createCardList(Long boardId, CreateCardListRequest request) {
        log.info("在看板 {} 中创建列表: {}", boardId, request.getName());
        
        Board board = boardRepository.findById(boardId)
            .orElseThrow(() -> new IllegalArgumentException("看板不存在: " + boardId));
        
        // 获取下一个可用的位置
        Double nextPosition = cardListRepository.findMaxPositionByBoardId(boardId)
            .map(max -> max + 1.0)
            .orElse(1.0);
        
        // 创建列表实体
        CardList cardList = CardList.create(request.getName(), nextPosition, board);
        cardList = cardListRepository.save(cardList);
        
        log.info("列表 {} 创建成功，ID: {}", cardList.getName(), cardList.getId());
        
        return dtoMapper.toCardListResponse(cardList);
    }

    /**
     * 更新列表名称
     * 需要是看板所属项目的成员
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, " +
                  "@cardListRepository.findById(#listId).get().getBoard().getId())")
    public CardListResponse updateCardList(Long listId, UpdateCardListRequest request) {
        log.info("更新列表 {}: {}", listId, request);
        
        CardList cardList = cardListRepository.findById(listId)
            .orElseThrow(() -> new IllegalArgumentException("列表不存在: " + listId));
        
        // 调用领域模型的业务方法
        cardList.updateName(request.getName());
        
        return dtoMapper.toCardListResponse(cardList);
    }

    /**
     * 删除列表
     * 需要是看板所属项目的成员
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, " +
                  "@cardListRepository.findById(#listId).get().getBoard().getId())")
    public void deleteCardList(Long listId) {
        log.warn("删除列表: {}", listId);
        
        CardList cardList = cardListRepository.findById(listId)
            .orElseThrow(() -> new IllegalArgumentException("列表不存在: " + listId));
        
        cardListRepository.delete(cardList);
        
        log.info("列表 {} 已删除", listId);
    }

    /**
     * 更新列表排序
     * 接收一个有序的列表 ID 数组，更新所有列表的 position 字段
     * 需要是看板所属项目的成员
     * 
     * 这是实现拖拽排序的关键方法
     */
    @PreAuthorize("@permissionService.isBoardMember(authentication, #boardId)")
    public List<CardListResponse> updateListOrder(Long boardId, UpdateListOrderRequest request) {
        log.info("更新看板 {} 的列表排序", boardId);
        
        List<Long> listIds = request.getListIds();
        
        // 验证所有列表都属于该看板
        List<CardList> cardLists = cardListRepository.findAllById(listIds);
        if (cardLists.size() != listIds.size()) {
            throw new IllegalArgumentException("列表ID列表包含无效的ID");
        }
        
        boolean allBelongToBoard = cardLists.stream()
            .allMatch(list -> list.belongsToBoard(boardId));
        if (!allBelongToBoard) {
            throw new IllegalArgumentException("列表不属于该看板");
        }
        
        // 更新位置（使用索引 * 1.0 作为新位置）
        for (int i = 0; i < listIds.size(); i++) {
            Long listId = listIds.get(i);
            CardList cardList = cardLists.stream()
                .filter(list -> list.getId().equals(listId))
                .findFirst()
                .orElseThrow();
            
            cardList.updatePosition((double) i);
        }
        
        log.info("看板 {} 的列表排序已更新", boardId);
        
        // 返回更新后的列表
        return cardLists.stream()
            .map(dtoMapper::toCardListResponse)
            .toList();
    }
}
