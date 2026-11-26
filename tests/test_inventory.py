from datetime import date, datetime
from decimal import Decimal
import pytest

from photostudio.employees.client import Client
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage
from photostudio.inventory.daily_report import DailyReport


class _DummyOrder:
    def __init__(self, order_id: int, status: str = "Прийнято", completed_at=None):
        self.orderId = order_id
        self.status = status
        self.completedAt = completed_at

    def getStatus(self) -> str:
        return self.status


class _DummyPayment:
    def __init__(self, amount, payment_date, paid: bool = True):
        self.amount = Decimal(str(amount))
        self.paymentDate = payment_date
        self._paid = paid

    def isPaid(self) -> bool:
        return self._paid


# --- 2.1.1 Client ---

def test_client_creation_and_orders():
    client = Client(1, "  Олена ", " Коваль ", " +380501234567 ")
    assert client.clientId == 1
    assert client.firstName == "Олена"
    assert client.lastName == "Коваль"
    assert client.phone == "+380501234567"

    order1 = _DummyOrder(101, "Прийнято")
    order2 = _DummyOrder(102, "Готово")

    client.addOrder(order1)
    client.addOrder(order2)
    client.addOrder(order1)  # дублікат не додається повторно

    orders = client.getOrders()
    assert len(orders) == 2
    assert client.getOrderStatus(order1) == "Прийнято"
    assert client.getOrderStatus(order2) == "Готово"


def test_client_invalid_data_and_unknown_order():
    with pytest.raises(ValueError):
        Client(0, "Олена", "Коваль", "+380501234567")
    with pytest.raises(ValueError):
        Client(1, "  ", "Коваль", "+380501234567")

    client = Client(1, "Олена", "Коваль", "+380501234567")
    outsider = _DummyOrder(999, "Видано")
    assert client.getOrderStatus(outsider) is None


# --- 2.1.2 PhotoMaterial: складські залишки, списання, нестача ---

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

    assert ink.writeOff(15) is True
    assert ink.getStockQuantity() == Decimal("5")
    assert ink.isBelowMinStock() is True

    # Нестача матеріалу: списати більше за поточний залишок не можна
    assert ink.writeOff(10) is False
    assert ink.getStockQuantity() == Decimal("5")

    # Некоректні значення списання
    assert ink.writeOff(0) is False
    assert ink.writeOff(-3) is False


# --- 2.1.3 MaterialUsage ---

def test_material_usage_validation():
    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")
    order = _DummyOrder(1, "В роботі")

    valid_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("12"), usageId=1)
    assert valid_usage.usageId == 1
    assert valid_usage.quantity == Decimal("12")
    assert valid_usage.validateQuantity() is True

    invalid_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("0"), usageId=2)
    assert invalid_usage.validateQuantity() is False


# --- 2.1.4 DailyReport ---

def test_daily_report_generation():
    target_day = date(2026, 11, 26)
    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")

    order_ready = _DummyOrder(1, "Готово", datetime(2026, 11, 26, 11, 0))
    order_issued = _DummyOrder(2, "Видано", datetime(2026, 11, 26, 14, 0))
    order_other_day = _DummyOrder(3, "Готово", datetime(2026, 11, 25, 14, 0))
    order_in_progress = _DummyOrder(4, "В роботі", datetime(2026, 11, 26, 15, 0))

    payments = [
        _DummyPayment("400.00", datetime(2026, 11, 26, 11, 5), paid=True),
        _DummyPayment("600.00", datetime(2026, 11, 26, 14, 5), paid=True),
        _DummyPayment("250.00", datetime(2026, 11, 26, 14, 10), paid=False),
        _DummyPayment("700.00", datetime(2026, 11, 25, 14, 5), paid=True),
    ]

    usages = [
        MaterialUsage(order_ready, paper, Decimal("6"), usageId=1, recordedAt=datetime(2026, 11, 26, 10, 50)),
        MaterialUsage(order_issued, paper, Decimal("4"), usageId=2, recordedAt=datetime(2026, 11, 26, 13, 50)),
        MaterialUsage(order_other_day, paper, Decimal("15"), usageId=3, recordedAt=datetime(2026, 11, 25, 13, 50)),
    ]

    report = DailyReport(reportDate=target_day, reportId=1)
    report.generate(
        orders=[order_ready, order_issued, order_other_day, order_in_progress],
        payments=payments,
        usages=usages,
    )

    assert report.completedOrders == 2
    assert report.totalRevenue == Decimal("1000.00")
    assert report.materialSummary == {"Фотопапір": Decimal("10")}
    assert "2026-11-26" in report.getSummary()
