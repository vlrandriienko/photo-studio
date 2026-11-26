import time
from decimal import Decimal

from photostudio.inventory.client import Client
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage


class _FastOrder:
    __slots__ = ("orderId", "clientId", "status", "quantity")

    def __init__(self, order_id: int, client_id: int, quantity: int, status: str = "Прийнято"):
        self.orderId = order_id
        self.clientId = client_id
        self.quantity = quantity
        self.status = status

    def getStatus(self):
        return self.status


def test_load_1000_orders_and_stock_checks():
    """3.1 Load Testing: час обробки 1 000 замовлень і перевірок складських залишків."""
    client = Client(1, "Тест", "Навантаження", "+380500000001")
    material = PhotoMaterial(1, "Фотопапір 10x15", Decimal("100000"), "арк.", minStock=Decimal("100"))

    start_time = time.perf_counter()

    for i in range(1, 1001):
        order = _FastOrder(order_id=i, client_id=client.clientId, quantity=1)
        client.addOrder(order)
        assert material.checkAvailability(1) is True
        assert material.getStockQuantity() >= Decimal("0")

    elapsed = time.perf_counter() - start_time
    assert len(client.getOrders()) == 1000
    assert elapsed < 5.0, f"Обробка 1 000 замовлень зайняла забагато часу: {elapsed:.4f} с"


def test_stress_10000_orders_stability_and_data_integrity():
    """3.2 Stress Testing: обробка 10 000 замовлень, стабільність і цілісність даних."""
    client = Client(2, "Стрес", "Тест", "+380500000002")
    material = PhotoMaterial(2, "Чорнила Matte Black", Decimal("50000"), "мл", minStock=Decimal("50"))
    usages_count = 0

    for i in range(1, 10001):
        order = _FastOrder(order_id=i, client_id=client.clientId, quantity=1, status="В роботі")
        client.addOrder(order)

        if i <= 10000 and material.checkAvailability(1):
            assert material.writeOff(1) is True
            usage = MaterialUsage(order=order, material=material, quantity=Decimal("1"))
            assert usage.validateQuantity() is True
            usages_count += 1

        assert material.getStockQuantity() >= Decimal("0")

    assert len(client.getOrders()) == 10000
    assert usages_count == 10000
    assert material.getStockQuantity() == Decimal("40000")
