from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from photostudio.employees.administrator import Administrator
from photostudio.employees.client import Client
from photostudio.employees.employee import Employee
from photostudio.employees.photographer import Photographer
from photostudio.employees.receptionist import Receptionist
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.orders.order import OrderStatus
from photostudio.orders.service import Service
from photostudio.studio import Studio


@pytest.fixture
def studio():
    studio = Studio()
    studio.addEmployee(Receptionist(1, "Приймальник", "reception", "1234", "001", studio.storage))
    studio.addEmployee(Photographer(2, "Фотограф", "photo", "1234", "002", studio.storage))
    studio.addEmployee(Administrator(3, "Адміністратор", "admin", "1234", "003", studio.storage))
    studio.addClient(Client(1, "Анна", "Тестова", "004"))
    studio.addService(Service(1, "Друк фото", "10.00", "шт."))
    studio.addMaterial(PhotoMaterial(1, "Фотопапір", 100, "шт.", 10))
    studio.setMaterialNorm(1, 1, 2)
    return studio


def create_order(studio, quantity=3, urgent=False, deadline=None):
    if deadline is None:
        deadline = datetime(2030, 1, 1, 12)
    return studio.createOrder(1, 1, 1, quantity, deadline, urgent)


def finish_order(studio, order):
    assert studio.startOrder(2, order.orderId) is True
    assert studio.registerMaterialUsage(2, order.orderId, 1, order.quantity * 2, f"finish-{order.orderId}") is True
    assert studio.completeOrder(2, order.orderId) is True


def test_employee_profile_and_password(studio):
    admin = studio.getEmployee(3)
    assert "Адміністратор" in admin.getProfile()
    assert "003" in admin.getProfile()
    assert "1234" not in admin.getProfile()
    assert admin.getLogin() == "admin"
    assert admin.verifyPassword("1234") is True
    assert admin.verifyPassword("wrong") is False
    assert admin.verifyPassword(None) is False


def test_employee_rejects_invalid_data():
    with pytest.raises(TypeError):
        Employee(1, "Працівник", "login", "1234", "001", {})
    with pytest.raises(ValueError):
        Administrator(0, "Анна", "admin", "1234", "001", {})
    with pytest.raises(ValueError):
        Administrator(1, "", "admin", "1234", "001", {})
    with pytest.raises(ValueError):
        Administrator(1, 123, "admin", "1234", "001", {})
    with pytest.raises(ValueError):
        Administrator(1, "Анна", "admin", "1234", "001", [])


def test_each_role_has_its_own_permissions(studio):
    receptionist = studio.getEmployee(1)
    photographer = studio.getEmployee(2)
    admin = studio.getEmployee(3)
    assert isinstance(receptionist, Employee)
    assert isinstance(photographer, Employee)
    assert isinstance(admin, Employee)
    assert receptionist.hasPermission("createOrder") is True
    assert receptionist.hasPermission("replenishMaterial") is False
    assert photographer.hasPermission("startOrder") is True
    assert photographer.hasPermission("issueOrder") is False
    assert admin.hasPermission("generateDailyReport") is True
    assert admin.hasPermission("recordPayment") is False
    assert admin.hasPermission("unknown") is False


def test_receptionist_creates_urgent_order(studio):
    order = create_order(studio, urgent=True)
    assert order.getTotalPrice() == Decimal("37.50")
    assert order.getStatus() == OrderStatus.accepted
    assert studio.storage["orders"] == [order]
    assert studio.getClient(1).getOrders() == [order]


def test_receptionist_rejects_invalid_order_quantity(studio):
    with pytest.raises(ValueError):
        create_order(studio, quantity=0)
    assert studio.storage["orders"] == []
    assert studio.getClient(1).getOrders() == []


def test_payment_and_issue_require_ready_order_and_correct_amount(studio):
    order = create_order(studio)
    assert studio.recordPayment(1, order.orderId, 30, "Картка") is False
    assert studio.issueOrder(1, order.orderId) is False

    finish_order(studio, order)
    assert studio.recordPayment(1, order.orderId, 29, "Картка") is False
    assert studio.issueOrder(1, order.orderId) is False
    assert studio.recordPayment(1, order.orderId, 30, "Картка") is True
    assert studio.recordPayment(1, order.orderId, 30, "Картка") is False
    assert studio.issueOrder(1, order.orderId) is True
    assert studio.issueOrder(1, order.orderId) is False
    assert order.getStatus() == OrderStatus.issued
    assert len(studio.storage["payments"]) == 1


def test_photographer_queue_prioritizes_urgent_orders_and_deadlines(studio):
    day = datetime(2030, 1, 1)
    normal = create_order(studio, deadline=day)
    urgent_late = create_order(studio, urgent=True, deadline=day + timedelta(days=2))
    urgent_early = create_order(studio, urgent=True, deadline=day + timedelta(days=1))
    active = create_order(studio)
    assert studio.startOrder(2, active.orderId) is True
    queue = studio.getEmployee(2).getOrderQueue()
    assert queue == [urgent_early, urgent_late, normal]


def test_photographer_can_resume_after_material_replenishment(studio):
    order = create_order(studio, quantity=60)
    assert studio.startOrder(2, order.orderId) is False
    assert order.getStatus() == OrderStatus.awaitingMaterials
    assert studio.getMaterial(1).getStockQuantity() == Decimal("100")
    assert studio.replenishMaterial(3, 1, 25) is True
    assert studio.startOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.inProgress


def test_photographer_cannot_finish_before_required_materials_are_used(studio):
    order = create_order(studio)
    assert studio.startOrder(2, order.orderId) is True
    assert studio.completeOrder(2, order.orderId) is False
    assert studio.registerMaterialUsage(2, order.orderId, 1, 6, "usage-1") is True
    assert studio.completeOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.ready
    assert order.completedAt is not None
    assert len(studio.storage["notifications"]) == 1
    assert studio.storage["notifications"][0].getStatus() is True


def test_material_usage_rejects_invalid_quantity_and_duplicate_write_off(studio):
    order = create_order(studio)
    assert studio.startOrder(2, order.orderId) is True
    assert studio.registerMaterialUsage(2, order.orderId, 1, 0, "invalid") is False
    assert studio.registerMaterialUsage(2, order.orderId, 1, 101, "too-much") is False
    assert studio.getMaterial(1).getStockQuantity() == Decimal("100")
    assert studio.registerMaterialUsage(2, order.orderId, 1, 6, "usage-1") is True
    assert studio.registerMaterialUsage(2, order.orderId, 1, 6, "usage-1") is True
    assert studio.registerMaterialUsage(2, order.orderId, 1, 7, "usage-1") is False
    assert studio.getMaterial(1).getStockQuantity() == Decimal("94")
    assert len(studio.storage["usages"]) == 1


def test_administrator_views_and_replenishes_materials(studio):
    admin = studio.getEmployee(3)
    materials = admin.getMaterials()
    assert materials == studio.storage["materials"]
    materials.clear()
    assert len(admin.getMaterials()) == 1
    assert admin.viewStock() == admin.getMaterials()
    assert studio.replenishMaterial(3, 1, -1) is False
    assert studio.replenishMaterial(3, 1, "5.5") is True
    assert studio.getMaterial(1).getStockQuantity() == Decimal("105.5")


def test_administrator_generates_daily_report(studio):
    order = create_order(studio)
    finish_order(studio, order)
    assert studio.recordPayment(1, order.orderId, 30, "Картка") is True
    report = studio.generateDailyReport(3, order.completedAt.date())
    assert report.completedOrders == 1
    assert report.totalRevenue == Decimal("30.00")
    assert report.materialSummary == {"Фотопапір": Decimal("6")}
    with pytest.raises(ValueError):
        studio.getEmployee(3).generateDailyReport("2030-01-01")
    with pytest.raises(ValueError):
        studio.getEmployee(3).generateDailyReport(datetime(2030, 1, 1, 12))


def test_receptionist_rejects_invalid_order_data(studio):
    receptionist = studio.getEmployee(1)
    client = studio.getClient(1)
    service = studio.getService(1)
    deadline = datetime(2030, 1, 1)

    with pytest.raises(ValueError):
        receptionist.createOrder("INVALID", None, service, 3, deadline)
    with pytest.raises(ValueError):
        receptionist.createOrder("", client, service, 3, deadline)
    with pytest.raises(ValueError):
        receptionist.createOrder("INVALID", client, service, 3, "2030-01-01")

    assert studio.storage["orders"] == []
    assert client.getOrders() == []


def test_receptionist_rejects_invalid_payment_data(studio):
    order = create_order(studio)
    finish_order(studio, order)
    receptionist = studio.getEmployee(1)

    assert receptionist.recordPayment(1, order, "abc", "Картка") is False
    assert receptionist.recordPayment(1, order, 30, None) is False
    assert receptionist.recordPayment(1, order, 30, "   ") is False
    assert studio.storage["payments"] == []
    assert order.getStatus() == OrderStatus.ready


def test_receptionist_keeps_payments_and_issue_separate_for_each_order(studio):
    first = create_order(studio)
    second = create_order(studio)
    finish_order(studio, first)
    finish_order(studio, second)
    receptionist = studio.getEmployee(1)

    assert receptionist.recordPayment(1, first, 30, "Картка") is True
    assert receptionist.recordPayment(2, first, 30, "Картка") is False
    assert receptionist.recordPayment(1, second, 30, "Картка") is False
    assert len(studio.storage["payments"]) == 1

    assert receptionist.issueOrder(second) is False
    assert second.getStatus() == OrderStatus.ready
    assert receptionist.issueOrder(first) is True
    assert receptionist.issueOrder(first) is False


def test_photographer_rejects_operations_in_wrong_status(studio):
    order = create_order(studio)
    photographer = studio.getEmployee(2)
    paper = studio.getMaterial(1)
    assert photographer.completeOrder(order) is False
    assert photographer.registerMaterialUsage(order, paper, 6, "too-early") is False
    assert photographer.startOrder(order) is True
    assert photographer.startOrder(order) is False
    assert paper.getStockQuantity() == Decimal("100")
    assert studio.storage["usages"] == []


def test_photographer_requires_material_configuration(studio):
    order = create_order(studio)
    del studio.storage["materialRequirements"][order.orderId]

    with pytest.raises(ValueError, match="потреби в матеріалах"):
        studio.getEmployee(2).startOrder(order)
    assert order.getStatus() == OrderStatus.accepted
    assert studio.getMaterial(1).getStockQuantity() == Decimal("100")


def test_photographer_sums_repeated_material_requirements(studio):
    order = create_order(studio)
    paper = studio.getMaterial(1)
    studio.storage["materialRequirements"][order.orderId] = [(paper, 4), (paper, 4)]
    photographer = studio.getEmployee(2)
    assert photographer.startOrder(order) is True
    assert photographer.registerMaterialUsage(order, paper, 6, "part-1") is True
    assert photographer.completeOrder(order) is False
    assert photographer.registerMaterialUsage(order, paper, 2, "part-2") is True
    assert photographer.completeOrder(order) is True
    assert paper.getStockQuantity() == Decimal("92")
