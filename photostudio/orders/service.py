from decimal import Decimal

class Service:
    def __init__(self, serviceId: int, name: str, baseTariff: Decimal | float | str, measurementUnit: str):
        tariff = Decimal(str(baseTariff))
        if tariff <= Decimal("0"):
            raise ValueError("Ціна послуги повинна бути більше нуля.")
        if not name or not name.strip():
            raise ValueError("Назва послуги не може бути порожньою.")

        self.__serviceId = serviceId
        self.__name = name.strip()
        self.__baseTariff = tariff
        self.__measurementUnit = measurementUnit.strip()

    @property
    def serviceId(self) -> int:
        return self.__serviceId

    @property
    def name(self) -> str:
        return self.__name

    @property
    def measurementUnit(self) -> str:
        return self.__measurementUnit

    def updatePrice(self, newTariff: Decimal | float | str) -> bool:
        tariff = Decimal(str(newTariff))
        if tariff <= Decimal("0"):
            return False
        self.__baseTariff = tariff
        return True

    def getTariff(self) -> Decimal:
        return self.__baseTariff

    def getServiceInfo(self) -> str:
        return f"{self.__name} — {self.__baseTariff} грн / {self.__measurementUnit}"