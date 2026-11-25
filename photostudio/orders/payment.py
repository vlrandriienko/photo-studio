from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from .order import OrderStatus


class Payment:
    def __init__(self, paymentId: int, orderId: str, amount: Decimal | float | str, paymentMethod: str):
        parsedAmount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if parsedAmount <= Decimal("0"):
            raise ValueError("Сума платежу повинна бути більшою за нуль.")

        self.__paymentId = paymentId
        self.__orderId = orderId
        self.__amount = parsedAmount
        self.__paymentDate: Optional[datetime] = None
        self.__paymentMethod = paymentMethod.strip()
        self.__isConfirmed = False

    @property
    def paymentId(self) -> int:
        return self.__paymentId

    @property
    def orderId(self) -> str:
        return self.__orderId

    @property
    def amount(self) -> Decimal:
        return self.__amount

    @property
    def paymentDate(self) -> Optional[datetime]:
        return self.__paymentDate

    @property
    def paymentMethod(self) -> str:
        return self.__paymentMethod

    def confirmPayment(self, expectedAmount: Decimal | float | str, orderStatus: OrderStatus) -> bool:
        if self.__isConfirmed:
            return False

        expected = Decimal(str(expectedAmount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if orderStatus != OrderStatus.ready:
            return False
        if self.__amount != expected:
            return False

        self.__isConfirmed = True
        self.__paymentDate = datetime.now()
        return True

    def isPaid(self) -> bool:
        return self.__isConfirmed

    def getPaymentDetails(self) -> str:
        statusText = "Підтверджено" if self.__isConfirmed else "Очікує підтвердження"
        dateText = self.__paymentDate.strftime("%Y-%m-%d %H:%M") if self.__paymentDate else "—"
        return (
            f"Платіж #{self.__paymentId} (Замовлення {self.__orderId}): "
            f"{self.__amount} грн | {self.__paymentMethod} | {statusText} ({dateText})"
        )