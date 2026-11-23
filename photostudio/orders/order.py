from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional
from .service import Service


class OrderStatus(Enum):
    ACCEPTED = "Прийнято"
    AWAITING_MATERIALS = "Очікує матеріали"
    IN_PROGRESS = "В роботі"
    READY = "Готово"
    ISSUED = "Видано"


class Order:
    _ALLOWED_TRANSITIONS = {
        OrderStatus.ACCEPTED: {OrderStatus.IN_PROGRESS, OrderStatus.AWAITING_MATERIALS},
        OrderStatus.AWAITING_MATERIALS: {OrderStatus.IN_PROGRESS},
        OrderStatus.IN_PROGRESS: {OrderStatus.READY},
        OrderStatus.READY: {OrderStatus.ISSUED},
        OrderStatus.ISSUED: set(),
    }

    URGENCY_MULTIPLIER = Decimal("1.25")

    def __init__(
        self,
        order_id: str,
        service: Service,
        quantity: int,
        desired_deadline: datetime,
        is_urgent: bool = False,
        client_id: Optional[int] = None,
        receptionist_id: Optional[int] = None,
    ):
        if not order_id or not order_id.strip():
            raise ValueError("Вкажіть номер замовлення.")
        if quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль.")

        self.__order_id = order_id.strip()
        self.__service = service
        self.__client_id = client_id
        self.__receptionist_id = receptionist_id
        self.__photographer_id: Optional[int] = None

        self.__created_at = datetime.now()
        self.__desired_deadline = desired_deadline
        self.__quantity = quantity
        self.__is_urgent = is_urgent

        self.__unit_price = service.get_tariff()
        self.__base_price = self.calculate_base_price()
        self.__total_price = self.calculate_total()

        self.__status = OrderStatus.ACCEPTED
        self.__completed_at: Optional[datetime] = None

    @property
    def order_id(self) -> str:
        return self.__order_id

    @property
    def service(self) -> Service:
        return self.__service

    @property
    def quantity(self) -> int:
        return self.__quantity

    @property
    def is_urgent(self) -> bool:
        return self.__is_urgent

    @property
    def created_at(self) -> datetime:
        return self.__created_at

    @property
    def desired_deadline(self) -> datetime:
        return self.__desired_deadline

    @property
    def completed_at(self) -> Optional[datetime]:
        return self.__completed_at

    @property
    def client_id(self) -> Optional[int]:
        return self.__client_id

    @property
    def photographer_id(self) -> Optional[int]:
        return self.__photographer_id

    def assign_photographer(self, photographer_id: int) -> None:
        self.__photographer_id = photographer_id

    def calculate_base_price(self) -> Decimal:
        self.__base_price = (self.__unit_price * Decimal(self.__quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return self.__base_price

    def calculate_total(self) -> Decimal:
        base = self.calculate_base_price()
        if self.__is_urgent:
            total = base * self.URGENCY_MULTIPLIER
        else:
            total = base
        self.__total_price = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.__total_price

    def set_urgency(self, urgent: bool) -> None:
        if self.__status != OrderStatus.ACCEPTED:
            raise ValueError("Змінювати терміновість можна лише для замовлення в статусі 'Прийнято'.")
        self.__is_urgent = urgent
        self.calculate_total()

    def change_status(self, new_status: OrderStatus) -> bool:
        if new_status not in self._ALLOWED_TRANSITIONS.get(self.__status, set()):
            return False

        self.__status = new_status
        if new_status == OrderStatus.READY:
            self.__completed_at = datetime.now()
        return True

    def can_be_issued(self, is_paid: bool) -> bool:
        return self.__status == OrderStatus.READY and is_paid is True

    def get_status(self) -> OrderStatus:
        return self.__status

    def get_total_price(self) -> Decimal:
        return self.__total_price