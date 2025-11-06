package org.xzq.aether.application.service.mapper;

import org.springframework.stereotype.Component;
import org.xzq.aether.application.dto.board.BoardDetailResponse;
import org.xzq.aether.application.dto.board.BoardResponse;
import org.xzq.aether.application.dto.board.CardListResponse;
import org.xzq.aether.application.dto.card.*;
import org.xzq.aether.application.dto.project.*;
import org.xzq.aether.domain.activity.ActivityLog;
import org.xzq.aether.domain.board.Board;
import org.xzq.aether.domain.board.Card;
import org.xzq.aether.domain.board.CardAssignment;
import org.xzq.aether.domain.board.CardList;
import org.xzq.aether.domain.project.Project;
import org.xzq.aether.domain.project.ProjectMember;
import org.xzq.aether.domain.user.User;

import java.util.List;
import java.util.stream.Collectors;

/**
 * DTO 映射器
 * 负责 Entity 和 DTO 之间的转换
 */
@Component
public class DtoMapper {

    // ============ Project 映射 ============

    public ProjectResponse toProjectResponse(Project project) {
        return ProjectResponse.builder()
            .id(project.getId())
            .name(project.getName())
            .description(project.getDescription())
            .ownerUid(project.getOwner().getUid())
            .ownerUsername(project.getOwner().getUsername())
            .memberCount(project.getMembers().size())
            .boardCount(project.getBoards().size())
            .createdAt(project.getCreatedAt())
            .updatedAt(project.getUpdatedAt())
            .build();
    }

    public ProjectDetailResponse toProjectDetailResponse(Project project) {
        return ProjectDetailResponse.builder()
            .id(project.getId())
            .name(project.getName())
            .description(project.getDescription())
            .ownerUid(project.getOwner().getUid())
            .ownerUsername(project.getOwner().getUsername())
            .members(project.getMembers().stream()
                .map(this::toProjectMemberResponse)
                .collect(Collectors.toList()))
            .boardCount(project.getBoards().size())
            .createdAt(project.getCreatedAt())
            .updatedAt(project.getUpdatedAt())
            .build();
    }

    public ProjectMemberResponse toProjectMemberResponse(ProjectMember member) {
        User user = member.getId().getUser();
        return ProjectMemberResponse.builder()
            .userUid(user.getUid())
            .username(user.getUsername())
            .email(user.getEmail())
            .avatarUrl(user.getAvatarUrl())
            .role(member.getRole())
            .joinedAt(member.getJoinedAt())
            .build();
    }

    // ============ Board 映射 ============

    public BoardResponse toBoardResponse(Board board) {
        int cardCount = board.getLists().stream()
            .mapToInt(list -> list.getCards().size())
            .sum();
            
        return BoardResponse.builder()
            .id(board.getId())
            .name(board.getName())
            .projectId(board.getProject().getId())
            .listCount(board.getLists().size())
            .cardCount(cardCount)
            .createdAt(board.getCreatedAt())
            .build();
    }

    public BoardDetailResponse toBoardDetailResponse(Board board) {
        return BoardDetailResponse.builder()
            .id(board.getId())
            .name(board.getName())
            .projectId(board.getProject().getId())
            .lists(board.getLists().stream()
                .map(this::toCardListResponse)
                .collect(Collectors.toList()))
            .createdAt(board.getCreatedAt())
            .build();
    }

    // ============ CardList 映射 ============

    public CardListResponse toCardListResponse(CardList cardList) {
        return CardListResponse.builder()
            .id(cardList.getId())
            .name(cardList.getName())
            .position(cardList.getPosition())
            .boardId(cardList.getBoard().getId())
            .cards(cardList.getCards().stream()
                .map(this::toCardResponse)
                .collect(Collectors.toList()))
            .build();
    }

    // ============ Card 映射 ============

    public CardResponse toCardResponse(Card card) {
        return CardResponse.builder()
            .id(card.getId())
            .title(card.getTitle())
            .position(card.getPosition())
            .listId(card.getList().getId())
            .dueDate(card.getDueDate())
            .assigneeCount(card.getAssignments().size())
            .createdAt(card.getCreatedAt())
            .updatedAt(card.getUpdatedAt())
            .build();
    }

    public CardDetailResponse toCardDetailResponse(Card card) {
        return CardDetailResponse.builder()
            .id(card.getId())
            .title(card.getTitle())
            .description(card.getDescription())
            .position(card.getPosition())
            .listId(card.getList().getId())
            .listName(card.getList().getName())
            .boardId(card.getList().getBoard().getId())
            .boardName(card.getList().getBoard().getName())
            .dueDate(card.getDueDate())
            .assignees(card.getAssignments().stream()
                .map(this::toCardAssigneeResponse)
                .collect(Collectors.toList()))
            .createdAt(card.getCreatedAt())
            .updatedAt(card.getUpdatedAt())
            .build();
    }

    public CardAssigneeResponse toCardAssigneeResponse(CardAssignment assignment) {
        User user = assignment.getId().getUser();
        return CardAssigneeResponse.builder()
            .userUid(user.getUid())
            .username(user.getUsername())
            .email(user.getEmail())
            .avatarUrl(user.getAvatarUrl())
            .assignedAt(assignment.getAssignedAt())
            .build();
    }
}
