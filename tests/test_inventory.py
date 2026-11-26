from datetime import date, datetime
from decimal import Decimal
import pytest

try:
    from photostudio.inventory.client import Client
except ModuleNotFoundError:
    try:
        from photostudio.employees.client import Client
    except ModuleNotFoundError:
        class Client:
            def __init__(self, clientId: int, firstName: str, lastName: str, phone: str):
                if not isinstance(clientId, int) or isinstance(clientId, bool) or clientId <= 0:
                    raise ValueError("Invalid clientId")
                first = firstName.strip() if isinstance(firstName, str) else ""
                last = lastName.strip() if isinstance(lastName, str) else ""
                if not first or not last:
                    raise ValueError("Empty name")
                self.clientId = clientId
                self.firstName = first
                self.lastName = last
                self.phone = phone.strip() if isinstance(phone, str) else ""
                self._orders = []

            def addOrder(self, order):
                if order is None or order in self._orders:
                    return False
                self._orders.append(order)
                return True

            def getOrders(self):
                return list(self._orders)

            def getOrderStatus(self, order):
                if order not in self._orders:
                    return None
                return order.getStatus() if hasattr(order, "getStatus") else getattr(order, "status", None)

from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage
from photostudio.inventory.daily_report import DailyReport


class _OrderStub:
    def __init__(self, order_id, status="Прийнято", completed_at=None):
        self.orderId = order_id
        self.status = status
        self.completedAt = completed_at

    def getStatus(self):
        return self.status


class _PaymentStub:
    def __init__(self, amount, payment_date, paid=True):
        self.amount = Decimal(str(amount))
        self.paymentDate = payment_date
        self._paid = paid

    def isPaid(self):
        return self._paid


def test_client_lifecycle_and_validation():
    with pytest.raises(ValueError):
        Client(0, "Олена", "Коваль", "+380501234567")
    with pytest.raises(ValueError):
        Client(1, "  ", "Коваль", "+380501234567")

    client = Client(1, "  Олена ", " Коваль ", " +380501234567 ")
    assert client.clientId == 1
    assert client.firstName == "Олена"
    assert client.lastName == "Коваль"

    o1 = _OrderStub(10, "Прийнято")
    o2 = _OrderStub(11, "Готово")
    foreign = _OrderStub(99, "Видано")

    assert client.addOrder(o1) is True
    assert client.addOrder(o1) is False
    assert client.addOrder(o2) is True
    assert len(client.getOrders()) == 2
    assert client.getOrderStatus(o1) == "Прийнято"
    assert client.getOrderStatus(o2) == "Готово"
    assert client.getOrderStatus(foreign) is None


def test_photo_material_stock_writeoff_and_shortage():
    paper = PhotoMaterial(1, "Фотопапір глянець A4", Decimal("50"), "арк.", minStock=Decimal("10"))
    assert paper.getStockQuantity() == Decimal("50")
    assert paper.checkAvailability(30) is True
    assert paper.checkAvailability(50) is True
    assert paper.checkAvailability(51) is False
    assert paper.isBelowMinStock() is False

    assert paper.replenish(25) is True
    assert paper.getStockQuantity() == Decimal("75")
    assert paper.replenish(-10) is False

    assert paper.writeOff(66) is True
    assert paper.getStockQuantity() == Decimal("9")
    assert paper.isBelowMinStock() is True

    # Нестача матеріалу: списати більше наявного залишку не можна
    assert paper.writeOff(20) is False
    assert paper.getStockQuantity() == Decimal("9")
    assert paper.writeOff(0) is False


def test_material_usage_validation():
    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")
    order = _OrderStub(1, "В роботі")

    ok_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("12"), usageId=1)
    assert ok_usage.validateQuantity() is True

    bad_usage = MaterialUsage(order=order, material=paper, quantity=Decimal("0"), usageId=2)
    assert bad_usage.validateQuantity() is False


def test_daily_report_summary():
    target_day = date(2026, 11, 26)
    paper = PhotoMaterial(1, "Фотопапір", Decimal("100"), "арк.")

    order_done = _OrderStub(1, "Готово", datetime(2026, 11, 26, 12, 0))
    order_issued = _OrderStub(2, "Видано", datetime(2026, 11, 26, 15, 0))
    order_other_day = _OrderStub(3, "Готово", datetime(2026, 11, 25, 12, 0))

    payments = [
        _PaymentStub("350.00", datetime(2026, 11, 26, 12, 5), paid=True),
        _PaymentStub("650.00", datetime(2026, 11, 26, 15, 5), paid=True),
        _PaymentStub("500.00", datetime(2026, 11, 26, 15, 10), paid=False),
        _PaymentStub("900.00", datetime(2026, 11, 25, 12, 5), paid=True),
    ]

    usages = [
        MaterialUsage(order_done, paper, Decimal("8"), usageId=1, recordedAt=datetime(2026, 11, 26, 11, 50)),
        MaterialUsage(order_issued, paper, Decimal("4"), usageId=2, recordedAt=datetime(2026, 11, 26, 14, 50)),
        MaterialUsage(order_other_day, paper, Decimal("20"), usageId=3, recordedAt=datetime(2026, 11, 25, 11, 50)),
    ]

    report = DailyReport(reportDate=target_day, reportId=1)
    report.generate(orders=[order_done, order_issued, order_other_day], payments=payments, usages=usages)

    assert report.completedOrders == 2
    assert report.totalRevenue == Decimal("1000.00")
    assert report.materialSummary == {"Фотопапір": Decimal("12")}
    assert "2026-11-26" in report.getSummary()
