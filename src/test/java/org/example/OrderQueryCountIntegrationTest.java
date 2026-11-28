package org.example;

import jakarta.persistence.EntityManagerFactory;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import org.example.dto.OrderPage;
import org.example.entity.Order;
import org.example.entity.OrderItem;
import org.example.entity.OrderStatus;
import org.example.entity.OrderType;
import org.example.entity.PaymentMethod;
import org.example.repository.OrderRepository;
import org.example.service.OrderService;
import org.example.shared.api.Role;
import org.hibernate.SessionFactory;
import org.hibernate.resource.jdbc.spi.StatementInspector;
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
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
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
        properties.add("spring.jpa.properties.hibernate.session_factory.statement_inspector",
                () -> SqlCapture.class.getName());
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

    @Test
    void bulkFetchReturnsDistinctRootsIncludingZeroItemOrderWithoutLazySelects() {
        insertOrder(4_101L, CUSTOMER_ID, "2026-10-07 10:00:00.000000");
        insertOrder(4_102L, CUSTOMER_ID, "2026-10-08 10:00:00.000000");
        insertItem(4_102L, 12_002L, 2L);
        insertItem(4_102L, 12_001L, 1L);

        statistics.clear();
        List<Order> fetched = orders.findWithItemsByIdIn(List.of(4_101L, 4_102L));

        assertEquals(2, fetched.size(), "Fetch join must de-duplicate root Orders");
        Order zeroItemOrder = fetched.stream()
                .filter(order -> order.getId() == 4_101L)
                .findFirst()
                .orElseThrow();
        Order multiItemOrder = fetched.stream()
                .filter(order -> order.getId() == 4_102L)
                .findFirst()
                .orElseThrow();
        assertTrue(zeroItemOrder.getItems().isEmpty(), "LEFT JOIN FETCH must preserve zero-item Orders");
        assertEquals(List.of(12_001L, 12_002L), multiItemOrder.getItems().stream()
                .map(OrderItem::getId)
                .toList());
        assertEquals(1L, statistics.getPrepareStatementCount(),
                "Accessing fetched items must not trigger a lazy SELECT per Order");
        assertEquals(0L, statistics.getCollectionFetchCount());
    }

    @Test
    void listContractPreservesScopedFiltersStablePagesAndTotals() {
        insertOrder(4_201L, CUSTOMER_ID, OrderStatus.COMPLETED, OrderType.DINE_IN,
                "2026-10-03 10:00:00.000000");
        insertItem(4_201L, 13_001L);
        insertOrder(4_202L, CUSTOMER_ID, OrderStatus.PENDING, OrderType.DELIVERY,
                "2026-10-04 10:00:00.000000");
        insertItem(4_202L, 13_002L);

        OrderPage first = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DINE_IN, 0, 20);
        OrderPage second = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DINE_IN, 1, 20);
        OrderPage last = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DINE_IN, 2, 20);
        OrderPage empty = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DINE_IN, 3, 20);

        assertPageMetadata(first, 0, 20, 50L, 20);
        assertPageMetadata(second, 1, 20, 50L, 20);
        assertPageMetadata(last, 2, 20, 50L, 10);
        assertPageMetadata(empty, 3, 20, 50L, 0);

        List<Long> allIds = java.util.stream.Stream.of(first, second, last)
                .flatMap(result -> result.content().stream())
                .map(order -> order.id())
                .toList();
        List<Long> expectedIds = java.util.stream.LongStream
                .rangeClosed(FIRST_ORDER_ID, FIRST_ORDER_ID + ORDER_COUNT - 1)
                .boxed()
                .sorted(java.util.Comparator.reverseOrder())
                .toList();
        assertEquals(expectedIds, allIds, "Tie ordering and page boundaries must be deterministic");
        assertEquals(ORDER_COUNT, new HashSet<>(allIds).size(), "Adjacent pages must not duplicate roots");

        OrderPage completed = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.COMPLETED, OrderType.DINE_IN, 0, 20);
        assertEquals(List.of(4_201L), completed.content().stream().map(order -> order.id()).toList());
        assertEquals(1L, completed.totalElements());

        OrderPage delivery = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DELIVERY, 0, 20);
        assertEquals(List.of(4_202L), delivery.content().stream().map(order -> order.id()).toList());
        assertEquals(1L, delivery.totalElements());

        OrderPage employeeQueue = service.list(2L, Role.EMPLOYEE, null, null, 0, 100);
        assertEquals(52L, employeeQueue.totalElements());
        assertEquals(List.of(4_202L, 3_001L), employeeQueue.content().stream()
                .limit(2)
                .map(order -> order.id())
                .toList());
        assertTrue(employeeQueue.content().stream().noneMatch(order -> order.id() == 4_201L));
    }

    @Test
    void listContractPreservesZeroAndMultiItemOrderDtos() {
        insertOrder(4_301L, CUSTOMER_ID, "2026-10-08 10:00:00.000000");
        insertOrder(4_302L, CUSTOMER_ID, "2026-10-08 10:00:00.000000");
        insertItem(4_302L, 14_002L, 2L);
        insertItem(4_302L, 14_001L, 1L);

        OrderPage page = service.list(CUSTOMER_ID, Role.CUSTOMER,
                OrderStatus.PENDING, OrderType.DINE_IN, 0, 2);

        assertPageMetadata(page, 0, 2, 52L, 2);
        assertEquals(List.of(4_302L, 4_301L), page.content().stream().map(order -> order.id()).toList());

        var multiItem = page.content().get(0);
        assertEquals(CUSTOMER_ID, multiItem.userId());
        assertEquals(OrderType.DINE_IN, multiItem.orderType());
        assertEquals(OrderStatus.PENDING, multiItem.status());
        assertEquals("B01", multiItem.tableNumber());
        assertEquals(PaymentMethod.CASH, multiItem.paymentMethod());
        assertNull(multiItem.recipientName());
        assertNull(multiItem.shippingPhone());
        assertNull(multiItem.shippingAddress());
        assertNull(multiItem.note());
        assertNull(multiItem.confirmedBy());
        assertNull(multiItem.confirmedAt());
        assertNull(multiItem.cancelledAt());
        assertNull(multiItem.completedAt());
        assertEquals(java.time.Instant.parse("2026-10-08T10:00:00Z"), multiItem.createdAt());
        assertEquals(multiItem.createdAt(), multiItem.updatedAt());
        assertEquals(List.of(1L, 2L), multiItem.items().stream().map(item -> item.foodId()).toList());
        assertTrue(multiItem.items().stream().allMatch(item -> item.foodName().equals("Phở bò tái")));
        assertTrue(multiItem.items().stream().allMatch(item -> item.unitPrice().equals(new BigDecimal("65000.00"))));
        assertTrue(multiItem.items().stream().allMatch(item -> item.quantity() == 1));
        assertTrue(multiItem.items().stream().allMatch(item -> item.lineTotal().equals(new BigDecimal("65000.00"))));
        assertEquals(new BigDecimal("130000.00"), multiItem.totalAmount());

        var zeroItem = page.content().get(1);
        assertTrue(zeroItem.items().isEmpty());
        assertEquals(new BigDecimal("0.00"), zeroItem.totalAmount());
    }

    @ParameterizedTest(name = "page size {0} uses three SELECTs without lazy item fetches")
    @ValueSource(ints = {1, 5, 20, 50})
    void orderListMustUseAtMostFourSelects(int size) {
        QueryResult result = listAndMeasure(size);

        assertPageFixture(result.page(), size);
        assertEquals(3, result.selects().size(), "Expected page IDs, joined Orders/items, and count SELECTs");
        assertEquals(0, result.collectionFetches(), "DTO mapping must not lazy-load order items");
        assertTrue(result.preparedStatements() <= 4,
                () -> "N+1 detected for page size " + size + ": captured "
                        + result.preparedStatements() + " statements; target is <= 4");
        assertEquals(1, result.selects().stream().filter(sql -> sql.contains(" left join order_items ")).count(),
                "Orders/items must be fetched in one joined SELECT");
        assertEquals(1, result.selects().stream().filter(sql -> sql.contains("select count(")).count(),
                "Total must use one explicit count SELECT");
        assertEquals(1, result.selects().stream().filter(sql -> sql.contains(" from orders ")
                && sql.contains(" order by ") && sql.contains(" limit ")
                && !sql.contains(" join ")).count(), "Only the Order ID query may paginate");
        assertTrue(result.selects().stream().filter(sql -> sql.contains(" left join order_items "))
                .noneMatch(sql -> sql.contains(" limit ")), "Collection fetch must not paginate");
        assertFalse(result.selects().stream().anyMatch(sql -> sql.contains(" from order_items ")),
                "No separate item SELECT may run for each Order");
        System.out.printf("G4-B-06 size=%d app SELECT=%d captured statements=%d collection fetches=%d%n",
                size, result.selects().size(), result.preparedStatements(), result.collectionFetches());
    }

    private QueryResult listAndMeasure(int size) {
        statistics.clear();
        SqlCapture.start();
        try {
            OrderPage page = service.list(CUSTOMER_ID, Role.CUSTOMER, null, null, 0, size);
            return new QueryResult(page, statistics.getPrepareStatementCount(),
                    statistics.getCollectionFetchCount(), SqlCapture.current());
        } finally {
            SqlCapture.stop();
        }
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

    private static void assertPageMetadata(OrderPage page, int expectedPage, int expectedSize,
                                           long expectedTotal, int expectedContentSize) {
        assertEquals(expectedPage, page.page());
        assertEquals(expectedSize, page.size());
        assertEquals(expectedTotal, page.totalElements());
        assertEquals(expectedContentSize, page.content().size());
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
        insertItem(orderId, itemId, 1L);
    }

    private void insertItem(long orderId, long itemId, long foodId) {
        db.update("""
                INSERT INTO order_items
                    (id, order_id, food_id, food_name, unit_price, quantity, created_at)
                VALUES (?, ?, ?, 'Phở bò tái', 65000.00, 1, '2026-10-01 10:00:00.000000')
                """, itemId, orderId, foodId);
    }

    private record QueryResult(OrderPage page, long preparedStatements, long collectionFetches,
                               List<String> selects) {}

    public static final class SqlCapture implements StatementInspector {
        private static final ThreadLocal<List<String>> SELECTS = new ThreadLocal<>();

        static void start() {
            SELECTS.set(new ArrayList<>());
        }

        static List<String> current() {
            List<String> selects = SELECTS.get();
            return selects == null ? List.of() : List.copyOf(selects);
        }

        static void stop() {
            SELECTS.remove();
        }

        @Override
        public String inspect(String sql) {
            List<String> selects = SELECTS.get();
            if (selects != null && sql.stripLeading().regionMatches(true, 0, "select", 0, 6)) {
                selects.add(sql.toLowerCase(java.util.Locale.ROOT).replaceAll("\\s+", " "));
            }
            return sql;
        }
    }
}
