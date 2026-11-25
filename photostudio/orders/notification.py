from datetime import datetime
from decimal import Decimal
from typing import Optional


class Notification:
    def __init__(self, notificationId: int, orderId: str, clientId: Optional[int] = None, messageText: str = ""):
        self.__notificationId = notificationId
        self.__orderId = orderId
        self.__clientId = clientId
        self.__messageText = messageText
        self.__createdAt = datetime.now()
        self.__isSent = False

    @property
    def notificationId(self) -> int:
        return self.__notificationId

    @property
    def orderId(self) -> str:
        return self.__orderId

    @property
    def clientId(self) -> Optional[int]:
        return self.__clientId

    @property
    def messageText(self) -> str:
        return self.__messageText

    @property
    def createdAt(self) -> datetime:
        return self.__createdAt

    def generateOrderReadyMessage(self, orderId: str, totalPrice: Decimal | float | str) -> None:
        self.__messageText = (
            f"Ваше замовлення #{orderId} готове до видачі! "
            f"До сплати: {Decimal(str(totalPrice)):.2f} грн."
        )

    def generateShortageMessage(self, orderId: str, materialName: str) -> None:
        self.__messageText = (
            f"Увага! Замовлення #{orderId} переведено в очікування через нестачу матеріалу: {materialName}."
        )

    def send(self) -> bool:
        if not self.__messageText.strip() or self.__isSent:
            return False
        self.__isSent = True
        return True

    def getStatus(self) -> bool:
        return self.__isSent