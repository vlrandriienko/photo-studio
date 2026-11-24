from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _to_decimal(value: Decimal | float | int | str) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        num = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not num.is_finite():
        return None
    return num


class PhotoMaterial:
    def __init__(
        self,
        materialId: int,
        name: str,
        stockQuantity: Decimal | float | int | str,
        unit: str,
        minStock: Decimal | float | int | str = Decimal("0"),
    ):
        if type(materialId) is not int or materialId <= 0:
            raise ValueError("ID матеріалу має бути додатним цілим числом.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Назва матеріалу не може бути порожньою.")
        if not isinstance(unit, str) or not unit.strip():
            raise ValueError("Одиниця виміру не може бути порожньою.")

        stock = _to_decimal(stockQuantity)
        min_stock = _to_decimal(minStock)
        if stock is None or stock < Decimal("0"):
            raise ValueError("Початковий залишок не може бути від'ємним.")
        if min_stock is None or min_stock < Decimal("0"):
            raise ValueError("Мінімальний залишок не може бути від'ємним.")

        self.__materialId = materialId
        self.__name = name.strip()
        self.__stockQuantity = stock
        self.__unit = unit.strip()
        self.__minStock = min_stock

    @property
    def materialId(self) -> int:
        return self.__materialId

    @property
    def name(self) -> str:
        return self.__name

    @property
    def unit(self) -> str:
        return self.__unit

    @property
    def minStock(self) -> Decimal:
        return self.__minStock

    def getStockQuantity(self) -> Decimal:
        return self.__stockQuantity

    def checkAvailability(self, quantity: Decimal | float | int | str) -> bool:
        qty = _to_decimal(quantity)
        if qty is None or qty <= Decimal("0"):
            return False
        return self.__stockQuantity >= qty

    def writeOff(self, quantity: Decimal | float | int | str) -> bool:
        qty = _to_decimal(quantity)
        if qty is None or qty <= Decimal("0"):
            return False
        if self.__stockQuantity < qty:
            return False
        self.__stockQuantity = (self.__stockQuantity - qty).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        ).normalize() if (self.__stockQuantity - qty) % 1 != 0 else (self.__stockQuantity - qty)
        return True

    def replenish(self, quantity: Decimal | float | int | str) -> bool:
        qty = _to_decimal(quantity)
        if qty is None or qty <= Decimal("0"):
            return False
        self.__stockQuantity += qty
        return True

    def isBelowMinStock(self) -> bool:
        return self.__stockQuantity <= self.__minStock
