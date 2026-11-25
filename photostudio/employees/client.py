from typing import Any, List


class Client:
    def __init__(self, clientId: int, firstName: str, lastName: str, phone: str):
        if type(clientId) is not int or clientId <= 0:
            raise ValueError("Ідентифікатор клієнта має бути додатним цілим числом.")
        for field in (firstName, lastName, phone):
            if not isinstance(field, str) or not field.strip():
                raise ValueError("Дані клієнта мають бути непорожніми рядками.")

        self.__clientId = clientId
        self.__firstName = firstName.strip()
        self.__lastName = lastName.strip()
        self.__phone = phone.strip()
        self.__orders: List[Any] = []

    @property
    def clientId(self) -> int:
        return self.__clientId

    @property
    def firstName(self) -> str:
        return self.__firstName

    @property
    def lastName(self) -> str:
        return self.__lastName

    @property
    def phone(self) -> str:
        return self.__phone

    def addOrder(self, order: Any) -> None:
        if order is not None and order not in self.__orders:
            self.__orders.append(order)

    def getOrders(self) -> List[Any]:
        return list(self.__orders)

    def getOrderStatus(self, order: Any) -> Any:
        if order not in self.__orders:
            return None
        return order.getStatus()
