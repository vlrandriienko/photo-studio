from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from enum import Enum


class Employee(ABC):
    def __init__(self, employeeId, fullName, login, passwordHash, phone, storage):
        if type(employeeId) is not int or employeeId <= 0:
            raise ValueError("Ідентифікатор має бути додатним цілим числом.")

        for value in [fullName, login, passwordHash, phone]:
            if not isinstance(value, str):
                raise ValueError("Дані працівника мають бути рядками.")
            if value.strip() == "":
                raise ValueError("Дані працівника не можуть бути порожніми.")

        if not isinstance(storage, dict):
            raise ValueError("Сховище має бути спільним словником.")

        self._employeeId = employeeId
        self._fullName = fullName.strip()
        self._phone = phone.strip()
        self.__login = login.strip()
        self.__passwordHash = passwordHash
        self._storage = storage

    def getProfile(self):
        return f"{self._employeeId}: {self._fullName}, тел. {self._phone}"

    @abstractmethod
    def hasPermission(self, action):
        pass

    def _positiveDecimal(self, value):
        if isinstance(value, bool):
            return None

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

        if not number.is_finite():
            return None
        if number <= 0:
            return None
        return number

    def _status(self, order):
        status = order.getStatus()
        if isinstance(status, Enum):
            return status.value
        return status
