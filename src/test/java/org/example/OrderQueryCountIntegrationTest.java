package org.example;

import jakarta.persistence.EntityManagerFactory;
import java.util.Collection;
import java.util.List;
import java.util.Objects;
import org.example.dto.OrderPage;
import org.example.entity.OrderStatus;
import org.example.entity.OrderType;
import org.example.repository.OrderRepository;
import org.example.service.OrderService;
import org.example.shared.api.Role;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.domain.PageRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MySQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class OrderQueryCountIntegrationTest {
    private static final long CUSTOMER_ID = 4L;
    private static final long FIRST_ORDER_ID = 2_001L;
    private static final int ORDER_COUNT = 50;

    @Container
    static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.4")
            .withDatabaseName("order_query_count")
            .withInitScript("db/schema.sql");

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", MYSQL::getJdbcUrl);
        properties.add("spring.datasource.username", MYSQL::getUsername);
        properties.add("spring.datasource.password", MYSQL::getPassword);
        properties.add("spring.jpa.properties.hibernate.generate_statistics", () -> "true");
        TestAuthKeys.register(properties);
    }

    @Autowired JdbcTemplate db;
    @Autowired OrderRepository orders;
    @Autowired OrderService service;
    @Autowired EntityManagerFactory entityManagerFactory;

    private Statistics statistics;

    @BeforeEach
    void seedOrdersWithItemsForScopeAndStableOrdering() {
        for (String table : List.of("order_items", "orders", "cart_items", "carts", "foods", "categories", "users")) {
            db.update("DELETE FROM " + table);
        }
        new ResourceDatabasePopulator(new ClassPathResource("db/seed.sql"))
                .execute(Objects.requireNonNull(db.getDataSource()));
        db.update("DELETE FROM order_items");
        db.update("DELETE FROM orders");

        for (int index = 0; index < ORDER_COUNT; index++) {
            long orderId = FIRST_ORDER_ID + index;
            insertOrder(orderId, CUSTOMER_ID, "2026-10-01 10:00:00.000000");
            insertItem(orderId, index + 1L);
        }

        // This newer order must not leak into the customer-scoped page.
        insertOrder(3_001L, 5L, "2026-10-02 10:00:00.000000");
        insertItem(3_001L, 10_001L);

        statistics = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        statistics.clear();
    }

    @Test
    void pageIdQueryAppliesScopeFiltersStableOrderAndNoImplicitCount() {
        insertOrder(4_001L, CUSTOMER_ID, OrderStatus.PENDING, OrderType.DINE_IN,
                "2026-10-03 10:00:00.000000");
        insertOrder(4_002L, CUSTOMER_ID, OrderStatus.PENDING, OrderType.DINE_IN,
                "2026-10-03 10:00:00.000000");
        insertOrder(4_003L, CUSTOMER_ID, OrderStatus.PENDING, OrderType.DELIVERY,
                "2026-10-04 10:00:00.000000");
        insertOrder(4_004L, CUSTOMER_ID, OrderStatus.COMPLETED, OrderType.DINE_IN,
                "2026-10-05 10:00:00.000000");
        insertOrder(4_005L, 5L, OrderStatus.PENDING, OrderType.DINE_IN,
                "2026-10-06 10:00:00.000000");

        assertEquals(List.of(4_002L, 4_001L), findPageIds(
                CUSTOMER_ID, List.of(OrderStatus.PENDING), OrderType.DINE_IN, 0, 2));
        assertEquals(List.of(2_050L, 2_049L), findPageIds(
                CUSTOMER_ID, List.of(OrderStatus.PENDING), OrderType.DINE_IN, 1, 2));
        assertEquals(List.of(4_003L), findPageIds(
                CUSTOMER_ID, List.of(OrderStatus.PENDING), OrderType.DELIVERY, 0, 10));
        assertEquals(List.of(4_004L), findPageIds(
                CUSTOMER_ID, List.of(OrderStatus.COMPLETED), OrderType.DINE_IN, 0, 10));
        assertEquals(List.of(4_005L), findPageIds(
                null, List.of(OrderStatus.PENDING), OrderType.DINE_IN, 0, 1));
    }

    @ParameterizedTest(name = "page size {0} exposes one lazy item SELECT per order")
    @ValueSource(ints = {1, 5, 20, 50})
    void baselineQueryCountGrowsWithPageSize(int size) {
        QueryResult result = listAndMeasure(size);

        assertPageFixture(result.page(), size);
        assertEquals(size, result.collectionFetches(),
                "Baseline phải phát hiện đúng một lazy collection fetch cho mỗi Order trong page");
        assertEquals(size + 2L, result.preparedStatements(),
                "Baseline service call gồm page SELECT, count SELECT và N item SELECT");
    }

    @ParameterizedTest(name = "page size {0} must fit the approved query budget")
    @ValueSource(ints = {1, 5, 20, 50})
    void orderListMustUseAtMostFourSelects(int size) {
        QueryResult result = listAndMeasure(size);

        assertPageFixture(result.page(), size);
        assertTrue(result.preparedStatements() <= 4,
                () -> "N+1 detected for page size " + size + ": captured "
                        + result.preparedStatements() + " statements; target is <= 4");
    }

    private QueryResult listAndMeasure(int size) {
        statistics.clear();
        OrderPage page = service.list(CUSTOMER_ID, Role.CUSTOMER, null, null, 0, size);
        return new QueryResult(page, statistics.getPrepareStatementCount(), statistics.getCollectionFetchCount());
    }

    private List<Long> findPageIds(Long userId, Collection<OrderStatus> statuses, OrderType type,
                                   int page, int size) {
        statistics.clear();
        List<Long> ids = orders.findPageIds(userId, statuses, type, PageRequest.of(page, size));
        assertEquals(1L, statistics.getPrepareStatementCount(),
                "Page-ID repository call must not trigger an implicit count query");
        return ids;
    }

    private static void assertPageFixture(OrderPage page, int size) {
        assertEquals(size, page.content().size());
        assertEquals(ORDER_COUNT, page.totalElements());
        assertTrue(page.content().stream().allMatch(order -> order.userId() == CUSTOMER_ID));
        assertTrue(page.content().stream().allMatch(order -> !order.items().isEmpty()));

        List<Long> expectedIds = java.util.stream.LongStream
                .rangeClosed(FIRST_ORDER_ID + ORDER_COUNT - size, FIRST_ORDER_ID + ORDER_COUNT - 1)
                .boxed()
                .sorted(java.util.Comparator.reverseOrder())
                .toList();
        assertEquals(expectedIds, page.content().stream().map(order -> order.id()).toList(),
                "Orders có cùng createdAt phải dùng id DESC và giữ customer scope");
    }

    private void insertOrder(long orderId, long userId, String createdAt) {
        insertOrder(orderId, userId, OrderStatus.PENDING, OrderType.DINE_IN, createdAt);
    }

    private void insertOrder(long orderId, long userId, OrderStatus status, OrderType type, String createdAt) {
        db.update("""
                INSERT INTO orders
                    (id, user_id, status, order_type, table_number, payment_method, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'B01', 'CASH', ?, ?)
                """, orderId, userId, status.name(), type.name(), createdAt, createdAt);
    }

    private void insertItem(long orderId, long itemId) {
        db.update("""
                INSERT INTO order_items
                    (id, order_id, food_id, food_name, unit_price, quantity, created_at)
                VALUES (?, ?, 1, 'Phở bò tái', 65000.00, 1, '2026-10-01 10:00:00.000000')
                """, itemId, orderId);
    }

    private record QueryResult(OrderPage page, long preparedStatements, long collectionFetches) {}
}
