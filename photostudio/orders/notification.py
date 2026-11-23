from datetime import datetime
from decimal import Decimal
from typing import Optional


class Notification:
    def __init__(self, notification_id: int, order_id: str, client_id: Optional[int] = None, message_text: str = ""):
        self.__notification_id = notification_id
        self.__order_id = order_id
        self.__client_id = client_id
        self.__message_text = message_text
        self.__created_at = datetime.now()
        self.__is_sent = False

    @property
    def notification_id(self) -> int:
        return self.__notification_id

    @property
    def order_id(self) -> str:
        return self.__order_id

    @property
    def client_id(self) -> Optional[int]:
        return self.__client_id

    @property
    def message_text(self) -> str:
        return self.__message_text

    @property
    def created_at(self) -> datetime:
        return self.__created_at

    def generate_order_ready_message(self, order_id: str, total_price: Decimal | float | str) -> None:
        self.__message_text = (
            f"Ваше замовлення #{order_id} готове до видачі! "
            f"До сплати: {Decimal(str(total_price)):.2f} грн."
        )

    def generate_shortage_message(self, order_id: str, material_name: str) -> None:
        self.__message_text = (
            f"Увага! Замовлення #{order_id} переведено в очікування через нестачу матеріалу: {material_name}."
        )

    def send(self) -> bool:
        if not self.__message_text.strip() or self.__is_sent:
            return False
        self.__is_sent = True
        return True

    def get_status(self) -> bool:
        return self.__is_sent