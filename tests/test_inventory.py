from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest

from photostudio.inventory.client import Client
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage
from photostudio.inventory.daily_report import DailyReport


class _DummyOrder:
    def __init__(self, order_id, status="Прийнято", total=Decimal("500.00"), completed_at=None, client=None):
        self.orderId = order_id
        self.status = status
        self.totalPrice = total
        self.completedAt = completed_at
        self.client = client

    def getStatus(self):
        return self.status

    def getTotalPrice(self):
        return self.totalPrice


class _DummyPayment:
    def __init__(self, amount, payment_date, is_paid=True):
        self.amount = Decimal(str(amount))
        self.paymentDate = payment_date
        self._paid = is_paid

    def isPaid(self):
        return self._paid


# --- Client ---

def test_client_creation_and_orders():
    client = Client(1, "  Олена ", " Коваль ", "+380501234567")
    assert client.clientId == 1
    assert client.firstName == "Олена"
    assert client.lastName == "Коваль"
    assert client.phone == "+380501234567"

    order1 = _DummyOrder(101, status="Прийнято", client=client)
    order2 = _DummyOrder(102, status="Готово", client=client)
    client.addOrder(order1)
    client.addOrder(order2)
    client.addOrder(order1)  # дублікат не має додаватися двічі

    orders = client.getOrders()
    assert len(orders) == 2
    assert client.getOrderStatus(order1) == "Прийнято"
    assert client.getOrderStatus(order2) == "Готово"


def test_client_invalid_data():
    with pytest.raises(ValueError):
        Client(0, "Олена", "Коваль", "+380501234567")
    with pytest.raises(ValueError):
        Client(1, "   ", "Коваль", "+380501234567")

    client = Client(1, "Олена", "Коваль", "+380501234567")
    outsider_order = _DummyOrder(999, status="В роботі")
    assert client.getOrderStatus(outsider_order) is None


# --- PhotoMaterial (складські залишки та списання) ---

def test_photo_material_stock_and_replenish():
    paper = PhotoMaterial(1, "Фотопапір глянець A4", Decimal("50"), "арк.", minStock=Decimal("10"))
    assert paper.getStockQuantity() == Decimal("50")
    assert paper.checkAvailability(30) is True
    assert paper.checkAvailability(50) is True
    assert paper.checkAvailability(51) is False
    assert paper.isBelowMinStock() is False

    assert paper.replenish(25) is True
    assert paper.getStockQuantity() == Decimal("75")
    assert paper.replenish(-5) is False


def test_photo_material_write_off_and_shortage():
    ink = PhotoMaterial(2, "Чорнила Cyan", Decimal("20"), "мл", minStock=Decimal("5"))

    # Успішне списання
    assert ink.writeOff(15) is True
    assert ink.getStockQuantity() == Decimal("5")
    assert ink.isBelowMinStock() is True

    # Нестача матеріалу: списати більше, ніж є на складі, не можна
    assert ink.writeOff(10) is False
    assert ink.getStockQuantity() == Decimal("5")

    # Некоректна кількість
    assert ink.writeOff(0) is False
    assert ink.writeOff(-2) is False


# --- MaterialUsage ---

def test_material_usage_validation():
    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")
    order = _DummyOrder(10, status="В роботі")

    valid_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("12.5"), usageId=1)
    assert valid_usage.usageId == 1
    assert valid_usage.quantity == Decimal("12.5")
    assert valid_usage.validateQuantity() is True

    zero_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("0"), usageId=2)
    assert zero_usage.validateQuantity() is False


# --- DailyReport ---

def test_daily_report_generation():
    target_day = date(2026, 11, 26)
    other_day = date(2026, 11, 25)

    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")
    order_ok_1 = _DummyOrder(1, status="Готово", completed_at=datetime(2026, 11, 26, 14, 30))
    order_ok_2 = _DummyOrder(2, status="Видано", completed_at=datetime(2026, 11, 26, 16, 0))
    order_old = _DummyOrder(3, status="Готово", completed_at=datetime(2026, 11, 25, 12, 0))
    order_wip = _DummyOrder(4, status="В роботі", completed_at=datetime(2026, 11, 26, 17, 0))

    payments = [
        _DummyPayment("450.00", datetime(2026, 11, 26, 14, 35), is_paid=True),
        _DummyPayment("800.00", datetime(2026, 11, 26, 16, 5), is_paid=True),
        _DummyPayment("999.00", datetime(2026, 11, 26, 16, 10), is_paid=False),
        _DummyPayment("300.00", datetime(2026, 11, 25, 12, 5), is_paid=True),
    ]

    usages = [
        MaterialUsage(order_ok_1, paper, Decimal("10"), usageId=10, recordedAt=datetime(2026, 11, 26, 13, 0)),
        MaterialUsage(order_ok_2, paper, Decimal("5"), usageId=11, recordedAt=datetime(2026, 11, 26, 15, 0)),
        MaterialUsage(order_old, paper, Decimal("20"), usageId=12, recordedAt=datetime(2026, 11, 25, 11, 0)),
    ]

    report = DailyReport(reportDate=target_day, reportId=1)
    report.generate(
        orders=[order_ok_1, order_ok_2, order_old, order_wip],
        payments=payments,
        usages=usages,
    )

    assert report.completedOrders == 2
    assert report.totalRevenue == Decimal("1250.00")
    assert report.materialSummary == {"Фотопапір": Decimal("15")}
    assert "2026-11-26" in report.getSummary()
