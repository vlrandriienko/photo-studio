from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from .order import OrderStatus


class Payment:
    def __init__(self, payment_id: int, order_id: str, amount: Decimal | float | str, payment_method: str):
        parsed_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if parsed_amount <= Decimal("0"):
            raise ValueError("Сума платежу повинна бути більшою за нуль.")

        self.__payment_id = payment_id
        self.__order_id = order_id
        self.__amount = parsed_amount
        self.__payment_date: Optional[datetime] = None
        self.__payment_method = payment_method.strip()
        self.__is_confirmed = False

    @property
    def payment_id(self) -> int:
        return self.__payment_id

    @property
    def order_id(self) -> str:
        return self.__order_id

    @property
    def amount(self) -> Decimal:
        return self.__amount

    @property
    def payment_date(self) -> Optional[datetime]:
        return self.__payment_date

    @property
    def payment_method(self) -> str:
        return self.__payment_method

    def confirm_payment(self, expected_amount: Decimal | float | str, order_status: OrderStatus) -> bool:
        if self.__is_confirmed:
            return False

        expected = Decimal(str(expected_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if order_status != OrderStatus.READY:
            return False
        if self.__amount != expected:
            return False

        self.__is_confirmed = True
        self.__payment_date = datetime.now()
        return True

    def is_paid(self) -> bool:
        return self.__is_confirmed

    def get_payment_details(self) -> str:
        status_text = "Підтверджено" if self.__is_confirmed else "Очікує підтвердження"
        date_text = self.__payment_date.strftime("%Y-%m-%d %H:%M") if self.__payment_date else "—"
        return (
            f"Платіж #{self.__payment_id} (Замовлення {self.__order_id}): "
            f"{self.__amount} грн | {self.__payment_method} | {status_text} ({date_text})"
        )