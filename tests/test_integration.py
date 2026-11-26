from datetime import datetime
from decimal import Decimal
import importlib

import pytest

from photostudio.employees.administrator import Administrator
from photostudio.employees.client import Client
from photostudio.employees.photographer import Photographer
from photostudio.employees.receptionist import Receptionist
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.orders.order import OrderStatus
from photostudio.orders.service import Service
from photostudio.storage import loadData, saveData
from photostudio.studio import Studio


@pytest.fixture
def studio():
    studio = Studio()
    studio.addEmployee(Receptionist(1, "Олена Приймальник", "reception", "1234", "0501111111", studio.storage))
    studio.addEmployee(Photographer(2, "Петро Фотограф", "photo", "1234", "0502222222", studio.storage))
    studio.addEmployee(Administrator(3, "Ірина Адміністратор", "admin", "1234", "0503333333", studio.storage))

    studio.addClient(Client(1, "Анна", "Клименко", "0671111111"))
    studio.addClient(Client(2, "Богдан", "Шевченко", "0672222222"))

    studio.addService(Service(1, "Друк фото", "10.00", "шт.", requiresMaterials=True))
    studio.addService(Service(2, "Реставрація фото", "200.00", "шт.", requiresMaterials=True))

    studio.addMaterial(PhotoMaterial(1, "Фотопапір", 100, "шт.", 10))
    studio.addMaterial(PhotoMaterial(2, "Чернила", 80, "мл.", 10))

    studio.setMaterialNorm(1, 1, 2)
    studio.setMaterialNorm(1, 2, 1)
    studio.setMaterialNorm(2, 1, 1)
    studio.setMaterialNorm(2, 2, 3)
    return studio


def create_test_order(studio, *, client_id=1, service_id=1, quantity=3, urgent=False, deadline=None):
    if deadline is None:
        deadline = datetime(2030, 1, 1, 12)
    return studio.createOrder(1, client_id, service_id, quantity, deadline, urgent)


def start_and_finish_order(studio, order, operation_prefix="integration"):
    assert studio.startOrder(2, order.orderId) is True
    for material, required_quantity in studio.storage["materialRequirements"][order.orderId]:
        operation_id = f"{operation_prefix}-{order.orderId}-{material.materialId}"
        assert studio.registerMaterialUsage(
            2, order.orderId, material.materialId, required_quantity, operation_id
        ) is True
    assert studio.completeOrder(2, order.orderId) is True
    return order


def test_full_order_workflow(studio):
    order = create_test_order(studio, urgent=True)

    assert order.getStatus() == OrderStatus.accepted
    assert order.getTotalPrice() == Decimal("37.50")
    assert studio.getClient(1).getOrders() == [order]
    assert studio.storage["orders"] == [order]

    assert studio.startOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.inProgress
    assert studio.registerMaterialUsage(2, order.orderId, 1, 6, "full-paper") is True
    assert studio.registerMaterialUsage(2, order.orderId, 2, 3, "full-ink") is True
    assert studio.getMaterial(1).getStockQuantity() == Decimal("94")
    assert studio.getMaterial(2).getStockQuantity() == Decimal("77")

    assert studio.completeOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.ready
    assert order.completedAt is not None
    assert len(studio.storage["usages"]) == 2

    notification = studio.storage["notifications"][0]
    assert notification.clientId == 1
    assert notification.orderId == order.orderId
    assert notification.getStatus() is True

    assert studio.recordPayment(1, order.orderId, "37.50", "Картка") is True
    assert len(studio.storage["payments"]) == 1
    assert studio.issueOrder(1, order.orderId) is True
    assert order.getStatus() == OrderStatus.issued

    report = studio.generateDailyReport(3, order.completedAt.date())
    assert report.completedOrders == 1
    assert report.totalRevenue == Decimal("37.50")
    assert report.materialSummary == {"Фотопапір": Decimal("6"), "Чернила": Decimal("3")}


def test_material_shortage_and_replenishment(studio):
    order = create_test_order(studio, quantity=60)

    assert studio.startOrder(2, order.orderId) is False
    assert order.getStatus() == OrderStatus.awaitingMaterials
    assert studio.getMaterial(1).getStockQuantity() == Decimal("100")
    assert studio.getMaterial(2).getStockQuantity() == Decimal("80")
    assert len(studio.storage["usages"]) == 0

    assert studio.replenishMaterial(3, 1, 30) is True
    assert studio.replenishMaterial(3, 2, 10) is True
    assert studio.startOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.inProgress

    assert studio.registerMaterialUsage(2, order.orderId, 1, 120, "shortage-paper") is True
    assert studio.registerMaterialUsage(2, order.orderId, 2, 60, "shortage-ink") is True
    assert studio.completeOrder(2, order.orderId) is True
    assert order.getStatus() == OrderStatus.ready
    assert studio.getMaterial(1).getStockQuantity() == Decimal("10")
    assert studio.getMaterial(2).getStockQuantity() == Decimal("30")
    assert len(studio.storage["usages"]) == 2


def test_notification_integration(studio):
    order = create_test_order(studio, client_id=2)

    assert studio.startOrder(2, order.orderId) is True
    assert studio.completeOrder(2, order.orderId) is False
    assert studio.storage["notifications"] == []

    assert studio.registerMaterialUsage(2, order.orderId, 1, 6, "notify-paper") is True
    assert studio.registerMaterialUsage(2, order.orderId, 2, 3, "notify-ink") is True
    assert studio.completeOrder(2, order.orderId) is True

    assert len(studio.storage["notifications"]) == 1
    notification = studio.storage["notifications"][0]
    assert notification.orderId == order.orderId
    assert notification.clientId == 2
    assert notification.getStatus() is True
    assert order.orderId in notification.messageText
    assert studio.completeOrder(2, order.orderId) is False
    assert len(studio.storage["notifications"]) == 1


def test_payment_and_issue_integration(studio):
    order = create_test_order(studio)

    assert studio.recordPayment(1, order.orderId, "30.00", "Готівка") is False
    assert studio.issueOrder(1, order.orderId) is False
    assert studio.storage["payments"] == []

    start_and_finish_order(studio, order)

    assert studio.recordPayment(1, order.orderId, "29.99", "Готівка") is False
    assert studio.issueOrder(1, order.orderId) is False
    assert studio.recordPayment(1, order.orderId, "30.00", "Картка") is True
    assert studio.recordPayment(1, order.orderId, "30.00", "Картка") is False
    assert len(studio.storage["payments"]) == 1

    assert studio.issueOrder(1, order.orderId) is True
    assert studio.issueOrder(1, order.orderId) is False
    assert order.getStatus() == OrderStatus.issued


def test_daily_report_integration(studio):
    previous_day = datetime(2030, 11, 25, 10)
    report_day = datetime(2030, 11, 26, 10)

    first = create_test_order(studio, client_id=1, quantity=2)
    start_and_finish_order(studio, first, "report-first")
    assert studio.recordPayment(1, first.orderId, "20.00", "Картка") is True

    second = create_test_order(
        studio,
        client_id=2,
        service_id=2,
        quantity=1,
        deadline=report_day,
    )
    start_and_finish_order(studio, second, "report-second")
    assert studio.recordPayment(1, second.orderId, "200.00", "Готівка") is True

    first_completed = previous_day.replace(hour=15)
    second_completed = report_day.replace(hour=15)
    first_payment = report_day.replace(hour=11)
    second_payment = report_day.replace(hour=16)

    first.__dict__["_Order__completedAt"] = first_completed
    second.__dict__["_Order__completedAt"] = second_completed
    studio.storage["payments"][0].__dict__["_Payment__paymentDate"] = first_payment
    studio.storage["payments"][1].__dict__["_Payment__paymentDate"] = second_payment

    for usage in studio.storage["usages"][:2]:
        usage.__dict__["_MaterialUsage__recordedAt"] = first_completed
    for usage in studio.storage["usages"][2:]:
        usage.__dict__["_MaterialUsage__recordedAt"] = second_completed

    previous_day_report = studio.generateDailyReport(3, previous_day.date())
    assert previous_day_report.completedOrders == 1
    assert previous_day_report.totalRevenue == Decimal("0")
    assert previous_day_report.materialSummary == {
        "Фотопапір": Decimal("4"),
        "Чернила": Decimal("2"),
    }

    report_day_report = studio.generateDailyReport(3, report_day.date())
    assert report_day_report.completedOrders == 1
    assert report_day_report.totalRevenue == Decimal("220.00")
    assert report_day_report.materialSummary == {
        "Фотопапір": Decimal("1"),
        "Чернила": Decimal("3"),
    }


def test_save_load_integration(studio, tmp_path, monkeypatch):
    order = create_test_order(studio, client_id=2, quantity=4)
    start_and_finish_order(studio, order, "save-load")
    assert studio.recordPayment(1, order.orderId, "40.00", "Картка") is True
    assert studio.issueOrder(1, order.orderId) is True

    data_file = tmp_path / "studio_data.json"
    studio_module = importlib.import_module("photostudio.studio")

    monkeypatch.setattr(studio_module, "saveData", lambda storage, norms: saveData(storage, norms, data_file))
    monkeypatch.setattr(studio_module, "loadData", lambda: loadData(data_file))

    studio.save()
    assert data_file.exists()

    restored = Studio()
    restored.load()

    restored_order = restored.getOrder(order.orderId)
    assert restored_order is not None
    assert restored_order.getStatus() == OrderStatus.issued
    assert restored_order.quantity == 4
    assert restored_order.clientId == 2
    assert restored_order.photographerId == 2
    assert restored_order.getTotalPrice() == Decimal("40.00")

    assert len(restored.storage["clients"]) == 2
    assert len(restored.storage["orders"]) == 1
    assert len(restored.storage["materials"]) == 2
    assert len(restored.storage["payments"]) == 1
    assert len(restored.storage["usages"]) == 2
    assert restored_order in restored.getClient(2).getOrders()
    assert restored.materialNorms == studio.materialNorms
    restored_operations = {
        operation_id: (
            operation["order"].orderId,
            operation["material"].materialId,
            operation["quantity"],
        )
        for operation_id, operation in restored.storage["usageOperations"].items()
    }
    original_operations = {
        operation_id: (
            operation["order"].orderId,
            operation["material"].materialId,
            operation["quantity"],
        )
        for operation_id, operation in studio.storage["usageOperations"].items()
    }
    assert restored_operations == original_operations

    restored_payment = restored.storage["payments"][0]
    assert restored_payment.orderId == restored_order.orderId
    assert restored_payment.isPaid() is True
    assert restored.storage["usages"][0].order is restored_order

    stock_before_duplicate = restored.getMaterial(1).getStockQuantity()
    usage_count_before_duplicate = len(restored.storage["usages"])
    operation_count_before_duplicate = len(restored.storage["usageOperations"])
    restored.registerMaterialUsage(
        2,
        restored_order.orderId,
        1,
        8,
        "save-load-ORD001-1",
    )
    assert restored.getMaterial(1).getStockQuantity() == stock_before_duplicate
    assert len(restored.storage["usages"]) == usage_count_before_duplicate
    assert len(restored.storage["usageOperations"]) == operation_count_before_duplicate