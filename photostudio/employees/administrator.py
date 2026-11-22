from datetime import date, datetime
from .employee import Employee


class Administrator(Employee):
    PERMISSIONS = [
        "getMaterials",
        "viewStock",
        "replenishMaterial",
        "generateDailyReport"
    ]

    def hasPermission(self, action):
        return action in self.PERMISSIONS

    def getMaterials(self):
        return list(self._storage["materials"])

    def viewStock(self):
        return self.getMaterials()

    def replenishMaterial(self, material, quantity):
        quantity = self._positiveDecimal(quantity)
        if quantity is None:
            return False

        return material.replenish(quantity)

    def generateDailyReport(self, reportDate):
        if not isinstance(reportDate, date):
            raise ValueError("Для звіту потрібна дата.")
        if isinstance(reportDate, datetime):
            raise ValueError("Для звіту потрібна дата без часу.")

        from ..inventory.daily_report import DailyReport

        report = DailyReport(reportDate=reportDate)
        report.generate(
            self._storage["orders"],
            self._storage["payments"],
            self._storage["usages"]
        )
        return report
