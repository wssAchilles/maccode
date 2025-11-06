package org.xzq.aether.domain.board;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.xzq.aether.domain.project.Project;
import org.xzq.aether.domain.user.User;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Card 领域实体单元测试
 * 测试卡片的核心业务逻辑
 */
@DisplayName("Card 领域实体测试")
class CardTests {

    private Board board;
    private CardList listA;
    private CardList listB;
    private User testUser;

    @BeforeEach
    void setUp() {
        // 准备测试数据
        testUser = new User();
        testUser.setUid("test-uid");
        testUser.setEmail("test@example.com");
        testUser.setUsername("Test User");

        Project project = Project.create("Test Project", "Test Description", testUser);

        board = Board.create("Test Board", project);
        listA = CardList.create("List A", 1.0, board);
        listB = CardList.create("List B", 2.0, board);
    }

    @Test
    @DisplayName("创建卡片 - 应成功创建并设置正确的属性")
    void testCreateCard() {
        // Given & When
        Card card = Card.create("Test Card", 1.0, listA);

        // Then
        assertThat(card).isNotNull();
        assertThat(card.getTitle()).isEqualTo("Test Card");
        assertThat(card.getPosition()).isEqualTo(1.0);
        assertThat(card.getList()).isEqualTo(listA);
    }

    @Test
    @DisplayName("移动卡片到新列表 - 应更新卡片的列表和位置")
    void testMoveToNewList() {
        // Given
        Card card = Card.create("Test Card", 1.0, listA);

        // When
        card.moveTo(listB, 2.5);

        // Then
        assertThat(card.getList()).isEqualTo(listB);
        assertThat(card.getPosition()).isEqualTo(2.5);
    }

    @Test
    @DisplayName("在同一列表内移动卡片 - 应只更新位置")
    void testMoveWithinSameList() {
        // Given
        Card card = Card.create("Test Card", 1.0, listA);

        // When
        card.moveTo(listA, 3.0);

        // Then
        assertThat(card.getList()).isEqualTo(listA);
        assertThat(card.getPosition()).isEqualTo(3.0);
    }

    @Test
    @DisplayName("更新卡片标题 - 应成功更新")
    void testUpdateTitle() {
        // Given
        Card card = Card.create("Original Title", 1.0, listA);

        // When
        card.update("New Title", null, null);

        // Then
        assertThat(card.getTitle()).isEqualTo("New Title");
    }

    @Test
    @DisplayName("更新卡片描述 - 应成功更新")
    void testUpdateDescription() {
        // Given
        Card card = Card.create("Test Card", 1.0, listA);

        // When
        card.update(null, "New Description", null);

        // Then
        assertThat(card.getDescription()).isEqualTo("New Description");
    }

    @Test
    @DisplayName("更新卡片标题为空 - 标题应保持不变")
    void testUpdateTitleWithNull() {
        // Given
        Card card = Card.create("Test Card", 1.0, listA);
        String originalTitle = card.getTitle();

        // When
        card.update(null, null, null);

        // Then - 标题应该保持不变
        assertThat(card.getTitle()).isEqualTo(originalTitle);
    }

    @Test
    @DisplayName("创建卡片时标题为空 - 应抛出异常")
    void testCreateCardWithNullTitle() {
        // When & Then
        assertThatThrownBy(() -> Card.create(null, 1.0, listA))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("标题不能为空");
    }

    @Test
    @DisplayName("移动到空列表 - 应抛出异常")
    void testMoveToNullList() {
        // Given
        Card card = Card.create("Test Card", 1.0, listA);

        // When & Then
        assertThatThrownBy(() -> card.moveTo(null, 2.0))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("目标列表不能为空");
    }

    @Test
    @DisplayName("验证卡片位置范围 - 应接受有效位置")
    void testValidPosition() {
        // Given & When
        Card card1 = Card.create("Card 1", 0.0, listA);
        Card card2 = Card.create("Card 2", 1.5, listA);
        Card card3 = Card.create("Card 3", 99999.0, listA);

        // Then
        assertThat(card1.getPosition()).isEqualTo(0.0);
        assertThat(card2.getPosition()).isEqualTo(1.5);
        assertThat(card3.getPosition()).isEqualTo(99999.0);
    }
}
