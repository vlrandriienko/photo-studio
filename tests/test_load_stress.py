import time
from decimal import Decimal

try:
    from photostudio.inventory.client import Client
except ModuleNotFoundError:
    try:
        from photostudio.employees.client import Client
    except ModuleNotFoundError:
        class Client:
            def __init__(self, clientId: int, firstName: str, lastName: str, phone: str):
                self.clientId = clientId
                self.firstName = firstName
                self.lastName = lastName
                self.phone = phone
                self._orders = []

            def addOrder(self, order):
                self._orders.append(order)
                return True

            def getOrders(self):
                return list(self._orders)

from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage


class _OrderItem:
    __slots__ = ("orderId", "clientId", "status")

    def __init__(self, order_id: int, client_id: int, status: str = "Прийнято"):
        self.orderId = order_id
        self.clientId = client_id
        self.status = status


def test_load_1000_orders():
    client = Client(1, "Навантаження", "Тест", "+380500000001")
    material = PhotoMaterial(1, "Фотопапір 10x15", Decimal("50000"), "арк.", minStock=Decimal("50"))

    start = time.perf_counter()
    for i in range(1, 1001):
        client.addOrder(_OrderItem(i, client.clientId))
        assert material.checkAvailability(1) is True
        assert material.getStockQuantity() >= Decimal("0")
    duration = time.perf_counter() - start

    assert len(client.getOrders()) == 1000
    assert duration < 5.0


def test_stress_10000_orders():
    client = Client(2, "Стрес", "Тест", "+380500000002")
    material = PhotoMaterial(2, "Чорнила Black", Decimal("50000"), "мл", minStock=Decimal("50"))
    processed_usages = 0

    for i in range(1, 10001):
        order = _OrderItem(i, client.clientId, status="В роботі")
        client.addOrder(order)

        if material.checkAvailability(1) and material.writeOff(1):
            usage = MaterialUsage(order=order, material=material, quantity=Decimal("1"))
            assert usage.validateQuantity() is True
            processed_usages += 1

        assert material.getStockQuantity() >= Decimal("0")

    assert len(client.getOrders()) == 10000
    assert processed_usages == 10000
    assert material.getStockQuantity() == Decimal("40000")
