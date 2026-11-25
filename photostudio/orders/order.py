from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional
from .service import Service


class OrderStatus(Enum):
    accepted = "Прийнято"
    awaitingMaterials = "Очікує матеріали"
    inProgress = "В роботі"
    ready = "Готово"
    issued = "Видано"


class Order:
    _allowedTransitions = {
        OrderStatus.accepted: {OrderStatus.inProgress, OrderStatus.awaitingMaterials},
        OrderStatus.awaitingMaterials: {OrderStatus.inProgress},
        OrderStatus.inProgress: {OrderStatus.ready},
        OrderStatus.ready: {OrderStatus.issued},
        OrderStatus.issued: set(),
    }

    urgencyMultiplier = Decimal("1.25")

    def __init__(
        self,
        orderId: str,
        service: Service,
        quantity: int,
        desiredDeadline: datetime,
        isUrgent: bool = False,
        clientId: Optional[int] = None,
        receptionistId: Optional[int] = None,
    ):
        if not orderId or not orderId.strip():
            raise ValueError("Вкажіть номер замовлення.")
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("Кількість має бути додатним цілим числом.")
        if not isinstance(desiredDeadline, datetime):
            raise ValueError("Бажаний термін має містити дату та час.")
        if type(isUrgent) is not bool:
            raise ValueError("Терміновість має бути логічним значенням.")
        if not isinstance(service, Service):
            raise ValueError("Некоректна послуга.")

        self.__orderId = orderId.strip()
        self.__service = service
        self.__clientId = clientId
        self.__receptionistId = receptionistId
        self.__photographerId: Optional[int] = None

        self.__createdAt = datetime.now()
        self.__desiredDeadline = desiredDeadline
        self.__quantity = quantity
        self.__isUrgent = isUrgent

        self.__unitPrice = service.getTariff()
        self.__basePrice = self.calculateBasePrice()
        self.__totalPrice = self.calculateTotal()

        self.__status = OrderStatus.accepted
        self.__completedAt: Optional[datetime] = None

    @property
    def orderId(self) -> str:
        return self.__orderId

    @property
    def service(self) -> Service:
        return self.__service

    @property
    def quantity(self) -> int:
        return self.__quantity

    @property
    def isUrgent(self) -> bool:
        return self.__isUrgent

    @property
    def createdAt(self) -> datetime:
        return self.__createdAt

    @property
    def desiredDeadline(self) -> datetime:
        return self.__desiredDeadline

    @property
    def completedAt(self) -> Optional[datetime]:
        return self.__completedAt

    @property
    def clientId(self) -> Optional[int]:
        return self.__clientId

    @property
    def photographerId(self) -> Optional[int]:
        return self.__photographerId

    def assignPhotographer(self, photographerId: int) -> None:
        self.__photographerId = photographerId

    def calculateBasePrice(self) -> Decimal:
        self.__basePrice = (self.__unitPrice * Decimal(self.__quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return self.__basePrice

    def calculateTotal(self) -> Decimal:
        base = self.calculateBasePrice()
        if self.__isUrgent:
            total = base * self.urgencyMultiplier
        else:
            total = base
        self.__totalPrice = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.__totalPrice

    def setUrgency(self, urgent: bool) -> None:
        if self.__status != OrderStatus.accepted:
            raise ValueError("Змінювати терміновість можна лише для замовлення в статусі 'Прийнято'.")
        self.__isUrgent = urgent
        self.calculateTotal()

    def changeStatus(self, newStatus: OrderStatus) -> bool:
        if newStatus not in self._allowedTransitions.get(self.__status, set()):
            return False

        self.__status = newStatus
        if newStatus == OrderStatus.ready:
            self.__completedAt = datetime.now()
        return True

    def canBeIssued(self, isPaid: bool) -> bool:
        return self.__status == OrderStatus.ready and isPaid is True

    def getStatus(self) -> OrderStatus:
        return self.__status

    def getTotalPrice(self) -> Decimal:
        return self.__totalPrice