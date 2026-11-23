from decimal import Decimal

class Service:
    def __init__(self, service_id: int, name: str, base_tariff: Decimal | float | str, measurement_unit: str):
        tariff = Decimal(str(base_tariff))
        if tariff <= Decimal("0"):
            raise ValueError("Ціна послуги повинна бути більше нуля.")
        if not name or not name.strip():
            raise ValueError("Назва послуги не може бути порожньою.")

        self.__service_id = service_id
        self.__name = name.strip()
        self.__base_tariff = tariff
        self.__measurement_unit = measurement_unit.strip()

    @property
    def service_id(self) -> int:
        return self.__service_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def measurement_unit(self) -> str:
        return self.__measurement_unit

    def update_price(self, new_tariff: Decimal | float | str) -> bool:
        tariff = Decimal(str(new_tariff))
        if tariff <= Decimal("0"):
            return False
        self.__base_tariff = tariff
        return True

    def get_tariff(self) -> Decimal:
        return self.__base_tariff

    def get_service_info(self) -> str:
        return f"{self.__name} — {self.__base_tariff} грн / {self.__measurement_unit}"