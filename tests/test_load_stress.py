import time
from decimal import Decimal

from photostudio.employees.client import Client
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage


class _SimpleOrder:
    __slots__ = ("orderId", "clientId", "status")

    def __init__(self, order_id: int, client_id: int, status: str = "Прийнято"):
        self.orderId = order_id
        self.clientId = client_id
        self.status = status

    def getStatus(self) -> str:
        return self.status


def test_load_1000_orders_and_stock_checks():
    """3.1 Load Testing: обробка 1 000 замовлень і перевірки складських залишків."""
    client = Client(1, "Навантаження", "Тест", "+380500000001")
    material = PhotoMaterial(1, "Фотопапір 10x15", Decimal("100000"), "арк.", minStock=Decimal("50"))

    start_time = time.perf_counter()

    for i in range(1, 1001):
        order = _SimpleOrder(i, client.clientId)
        client.addOrder(order)
        assert material.checkAvailability(1) is True
        assert material.getStockQuantity() >= Decimal("0")

    elapsed_time = time.perf_counter() - start_time

    assert len(client.getOrders()) == 1000
    assert elapsed_time < 5.0


def test_stress_10000_orders_stability_and_integrity():
    """3.2 Stress Testing: обробка 10 000 замовлень, стабільність і цілісність даних."""
    client = Client(2, "Стрес", "Тест", "+380500000002")
    material = PhotoMaterial(2, "Чорнила Black", Decimal("50000"), "мл", minStock=Decimal("50"))
    valid_usages = 0

    for i in range(1, 10001):
        order = _SimpleOrder(i, client.clientId, status="В роботі")
        client.addOrder(order)

        if material.checkAvailability(1) and material.writeOff(1):
            usage = MaterialUsage(order=order, material=material, quantity=Decimal("1"))
            assert usage.validateQuantity() is True
            valid_usages += 1

        assert material.getStockQuantity() >= Decimal("0")

    assert len(client.getOrders()) == 10000
    assert valid_usages == 10000
    assert material.getStockQuantity() == Decimal("40000")
