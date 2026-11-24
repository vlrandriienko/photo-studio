from datetime import datetime
from decimal import Decimal
from typing import Any
from .photo_material import _to_decimal


class MaterialUsage:
    _next_usage_id = 1

    def __init__(
        self,
        order: Any,
        material: Any,
        quantity: Decimal | float | int | str,
        usageId: int | None = None,
        recordedAt: datetime | None = None,
    ):
        if order is None or material is None:
            raise ValueError("Потрібно вказати замовлення та фотоматеріал.")

        qty = _to_decimal(quantity)
        if qty is None:
            raise ValueError("Некоректна кількість використаного матеріалу.")

        if usageId is None:
            usageId = MaterialUsage._next_usage_id
            MaterialUsage._next_usage_id += 1
        elif type(usageId) is not int or usageId <= 0:
            raise ValueError("ID запису витрати має бути додатним цілим числом.")

        self.__usageId = usageId
        self.__order = order
        self.__material = material
        self.__quantity = qty
        self.__recordedAt = recordedAt if recordedAt is not None else datetime.now()

    @property
    def usageId(self) -> int:
        return self.__usageId

    @property
    def order(self) -> Any:
        return self.__order

    @property
    def material(self) -> Any:
        return self.__material

    @property
    def quantity(self) -> Decimal:
        return self.__quantity

    @property
    def recordedAt(self) -> datetime:
        return self.__recordedAt

    def validateQuantity(self) -> bool:
        return self.__quantity > Decimal("0")
