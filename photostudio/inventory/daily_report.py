from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List


def _extract_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _status_value(order: Any) -> str:
    raw = order.getStatus() if hasattr(order, "getStatus") else getattr(order, "status", "")
    return getattr(raw, "value", raw)


class DailyReport:
    _next_report_id = 1

    def __init__(self, reportDate: date, reportId: int | None = None):
        if not isinstance(reportDate, date) or isinstance(reportDate, datetime):
            raise ValueError("reportDate має бути об'єктом date без часу.")

        if reportId is None:
            reportId = DailyReport._next_report_id
            DailyReport._next_report_id += 1
        elif type(reportId) is not int or reportId <= 0:
            raise ValueError("ID звіту має бути додатним цілим числом.")

        self.__reportId = reportId
        self.__reportDate = reportDate
        self.__completedOrders: int = 0
        self.__totalRevenue: Decimal = Decimal("0")
        self.__materialSummary: Dict[str, Decimal] = {}

    @property
    def reportId(self) -> int:
        return self.__reportId

    @property
    def reportDate(self) -> date:
        return self.__reportDate

    @property
    def completedOrders(self) -> int:
        return self.__completedOrders

    @property
    def totalRevenue(self) -> Decimal:
        return self.__totalRevenue

    @property
    def materialSummary(self) -> Dict[str, Decimal]:
        return dict(self.__materialSummary)

    def generate(
        self,
        orders: Iterable[Any],
        payments: Iterable[Any],
        usages: Iterable[Any],
    ) -> None:
        completed_count = 0
        for order in orders:
            status = _status_value(order)
            if status not in ("Готово", "Видано"):
                continue
            completed_at = getattr(order, "completedAt", None)
            if _extract_date(completed_at) == self.__reportDate:
                completed_count += 1

        revenue = Decimal("0")
        for payment in payments:
            is_confirmed = (
                payment.isPaid()
                if hasattr(payment, "isPaid")
                else bool(getattr(payment, "is_confirmed", getattr(payment, "isConfirmed", False)))
            )
            if not is_confirmed:
                continue
            pay_date = getattr(payment, "paymentDate", None)
            if pay_date is None:
                pay_date = getattr(payment, "payment_date", getattr(payment, "paidAt", None))
            if _extract_date(pay_date) == self.__reportDate:
                amount = getattr(payment, "amount", Decimal("0"))
                revenue += Decimal(str(amount))

        summary: Dict[str, Decimal] = {}
        for usage in usages:
            recorded_at = getattr(usage, "recordedAt", None)
            if _extract_date(recorded_at) != self.__reportDate:
                continue
            qty = Decimal(str(getattr(usage, "quantity", Decimal("0"))))
            if qty <= Decimal("0"):
                continue
            mat = getattr(usage, "material", None)
            mat_name = getattr(mat, "name", str(mat)) if mat is not None else "Невідомий матеріал"
            summary[mat_name] = summary.get(mat_name, Decimal("0")) + qty

        self.__completedOrders = completed_count
        self.__totalRevenue = revenue
        self.__materialSummary = summary

    def getSummary(self) -> str:
        materials_part = (
            ", ".join(f"{name}: {qty}" for name, qty in self.__materialSummary.items())
            if self.__materialSummary
            else "немає"
        )
        return (
            f"Звіт #{self.__reportId} за {self.__reportDate.isoformat()}: "
            f"готових замовлень — {self.__completedOrders}, "
            f"виручка — {self.__totalRevenue} грн, "
            f"матеріали — {materials_part}."
        )
