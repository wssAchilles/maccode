这份文档就是你数据库的**“最高准则” (Highest Principle)**。

作为你的项目架构师，我将为你提供完整的数据库结构设计。你（和你的 AI Agent）的职责**不是**编写 SQL，而是根据这份蓝图，在 `com.aether.platform.domain` 包中创建对应的 **Java 实体类 (Entity)**。

你的 Spring Boot 配置（`spring.jpa.hibernate.ddl-auto=update`）会**自动**读取这些实体类，并在你的 MySQL `aether_db` 数据库中**自动创建和更新**这些表。

---

### 核心设计原则

1.  **实体优先 (Entity-First):** Java `@Entity` 类是唯一的事实来源。
2.  **外键关联:** 我们不直接存储 `id`，而是通过 `@ManyToOne` / `@OneToMany` 等注解来**映射对象关系**，JPA 会自动处理外键列。
3.  **命名规范:**
    * **Java 类名:** 大驼峰 (e.g., `CardList`)
    * **SQL 表名:** 蛇形 (e.g., `card_lists`) (JPA 会自动转换)

---

### 数据库实体蓝图 (Database Entity Blueprint)

总共 8 个核心表，它们构成了 "aether" 的骨架。

#### 1. 用户表 (The User Table)

* **职责:** 存储从 Firebase 同步过来的用户信息。这是所有“人”相关联的根。
* **Java 类名:** `User`
* **数据库表名:** `users`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `uid` | `String` | `VARCHAR(255)` | **主键 (Primary Key)**, `NOT NULL` | **[关键]** 必须是 Firebase UID，**不是**自增 ID。 |
| `email` | `String` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | |
| `username` | `String` | `VARCHAR(255)` | `NOT NULL` | |
| `avatar_url` | `String` | `VARCHAR(1024)` | `NULLABLE` | |
| `created_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | 审计字段，JPA 自动填充 |
| `updated_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | 审计字段，JPA 自动填充 |

**核心关系 (JPA):**
* `@OneToMany` -> 关联 `ProjectMember` (我是哪些项目的成员)
* `@OneToMany` -> 关联 `CardAssignment` (我被指派了哪些卡片)

#### 2. 项目表 (The Project Table)

* **职责:** 顶层工作空间，看板的容器。
* **Java 类名:** `Project`
* **数据库表名:** `projects`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Long` | `BIGINT` | **主键 (Primary Key)**, `AUTO_INCREMENT` | |
| `name` | `String` | `VARCHAR(255)` | `NOT NULL` | |
| `description` | `String` | `TEXT` | `NULLABLE` | |
| `owner_uid` | `User` | `VARCHAR(255)` | `NOT NULL`, **外键 -> `users(uid)`** | **[关键]** 指向 `User` 实体 (`@ManyToOne`) |
| `created_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |
| `updated_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

**核心关系 (JPA):**
* `@ManyToOne` -> 关联 `User` (这个项目的拥有者是谁)
* `@OneToMany` -> 关联 `ProjectMember` (这个项目的所有成员)
* `@OneToMany` -> 关联 `Board` (这个项目下的所有看板)

#### 3. 项目成员表 (The ProjectMember Table)

* **职责:** `User` 和 `Project` 之间的“多对多”关联表，并**附加了“角色”信息**。
* **Java 类名:** `ProjectMember`
* **数据库表名:** `project_members`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `ProjectMemberId` | (Composite) | **复合主键** | 见下方 `ProjectMemberId` 类 |
| `role` | `ProjectRole` (Enum) | `VARCHAR(50)` | `NOT NULL` | Enum 值: `OWNER`, `ADMIN`, `MEMBER` |
| `joined_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

**`ProjectMemberId` (复合主键类):**
* **职责:** 用于 `ProjectMember` 的复合主键。
* **Java 类名:** `ProjectMemberId` (使用 `@EmbeddableId`)
* `@ManyToOne` -> `Project project` (映射到 `project_id` 外键)
* `@ManyToOne` -> `User user` (映射到 `user_uid` 外键)

#### 4. 看板表 (The Board Table)

* **职责:** 卡片列表 (List) 的容器，隶属于一个项目。
* **Java 类名:** `Board`
* **数据库表名:** `boards`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Long` | `BIGINT` | **主键 (Primary Key)**, `AUTO_INCREMENT` | |
| `name` | `String` | `VARCHAR(255)` | `NOT NULL` | |
| `project_id` | `Project` | `BIGINT` | `NOT NULL`, **外键 -> `projects(id)`** | 指向 `Project` 实体 (`@ManyToOne`) |
| `created_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

**核心关系 (JPA):**
* `@ManyToOne` -> 关联 `Project` (我属于哪个项目)
* `@OneToMany` -> 关联 `CardList` (我包含哪些列表) ( **必须**使用 `@OrderBy("position ASC")` )

#### 5. 卡片列表 (The CardList Table)

* **职责:** 卡片 (Card) 的容器，隶属于一个看板，**必须支持排序**。
* **Java 类名:** `CardList`
* **数据库表名:** `card_lists`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Long` | `BIGINT` | **主键 (Primary Key)**, `AUTO_INCREMENT` | |
| `name` | `String` | `VARCHAR(255)` | `NOT NULL` | e.g., "待办", "进行中" |
| `position` | `Double` | `DOUBLE` | `NOT NULL` | **[关键]** 排序字段。使用 `Double` 而非 `Integer`，以便在两个列表间插入时只需计算中间值 (如 1.5)，避免更新大量数据。|
| `board_id` | `Board` | `BIGINT` | `NOT NULL`, **外键 -> `boards(id)`** | 指向 `Board` 实体 (`@ManyToOne`) |

**核心关系 (JPA):**
* `@ManyToOne` -> 关联 `Board` (我属于哪个看板)
* `@OneToMany` -> 关联 `Card` (我包含哪些卡片) ( **必须**使用 `@OrderBy("position ASC")` )

#### 6. 卡片表 (The Card Table)

* **职责:** 最小的任务单元，隶属于一个列表，**必须支持排序**。
* **Java 类名:** `Card`
* **数据库表名:** `cards`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Long` | `BIGINT` | **主键 (Primary Key)**, `AUTO_INCREMENT` | |
| `title` | `String` | `VARCHAR(255)` | `NOT NULL` | |
| `description` | `String` | `TEXT` | `NULLABLE` | |
| `position` | `Double` | `DOUBLE` | `NOT NULL` | **[关键]** 排序字段。同 `CardList.position`。|
| `due_date` | `Instant` | `TIMESTAMP` | `NULLABLE` | 截止日期 |
| `list_id` | `CardList` | `BIGINT` | `NOT NULL`, **外键 -> `card_lists(id)`** | 指向 `CardList` 实体 (`@ManyToOne`) |
| `created_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |
| `updated_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

**核心关系 (JPA):**
* `@ManyToOne` -> 关联 `CardList` (我属于哪个列表)
* `@ManyToMany` -> 关联 `User` (通过 `card_assignments` 表，指派给哪些人)

#### 7. 卡片指派表 (The CardAssignment Table)

* **职责:** `Card` 和 `User` 之间的“多对多”关联表。
* **Java 类名:** `CardAssignment` (推荐显式创建)
* **数据库表名:** `card_assignments`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `CardAssignmentId` | (Composite) | **复合主键** | 类似于 `ProjectMemberId` |
| `assigned_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

**`CardAssignmentId` (复合主键类):**
* `@ManyToOne` -> `Card card` (映射到 `card_id` 外键)
* `@ManyToOne` -> `User user` (映射到 `user_uid` 外键)

#### 8. 活动日志表 (The ActivityLog Table)

* **职责:** 异步存储项目中的所有活动记录（“谁在何时做了什么”）。
* **Java 类名:** `ActivityLog`
* **数据库表名:** `activity_logs`

| 字段名 (Column) | Java 类型 (Type) | SQL 类型 (Type) | 约束 (Constraints) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `Long` | `BIGINT` | **主键 (Primary Key)**, `AUTO_INCREMENT` | |
| `message` | `String` | `TEXT` | `NOT NULL` | e.g., "Achilles 将卡片 'X' 移到了 '已完成'" |
| `project_id` | `Project` | `BIGINT` | `NOT NULL`, **外键 -> `projects(id)`** | 用于快速筛选 (`@ManyToOne`) |
| `user_uid` | `User` | `VARCHAR(255)` | `NOT NULL`, **外键 -> `users(uid)`** | 操作者 (`@ManyToOne`) |
| `created_at` | `Instant` | `TIMESTAMP` | `NOT NULL` | |

---

