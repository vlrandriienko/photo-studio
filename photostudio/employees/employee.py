import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from enum import Enum


class Employee(ABC):
    _passwordIterations = 600_000

    def __init__(self, employeeId, fullName, login, password, phone, storage):
        if type(employeeId) is not int or employeeId <= 0:
            raise ValueError("Ідентифікатор має бути додатним цілим числом.")

        for value in [fullName, login, password, phone]:
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
        salt = secrets.token_bytes(16)
        passwordHash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self._passwordIterations
        )
        self.__passwordHash = (
            f"pbkdf2_sha256${self._passwordIterations}${salt.hex()}${passwordHash.hex()}"
        )
        self._storage = storage

    def getProfile(self):
        return f"{self._employeeId}: {self._fullName}, тел. {self._phone}"

    def getLogin(self) -> str:
        return self.__login

    def verifyPassword(self, password: str) -> bool:
        if not isinstance(password, str):
            return False

        try:
            algorithm, iterations, saltHex, passwordHashHex = self.__passwordHash.split("$")
            if algorithm != "pbkdf2_sha256" or int(iterations) != self._passwordIterations:
                return False
            salt = bytes.fromhex(saltHex)
            expectedHash = bytes.fromhex(passwordHashHex)
        except ValueError:
            return False

        actualHash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self._passwordIterations
        )
        return hmac.compare_digest(actualHash, expectedHash)

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
