from .employee import Employee


class Photographer(Employee):
    PERMISSIONS = [
        "getOrderQueue",
        "startOrder",
        "completeOrder",
        "registerMaterialUsage"
    ]

    def hasPermission(self, action):
        return action in self.PERMISSIONS

    def getOrderQueue(self):
        queue = []
        for order in self._storage["orders"]:
            status = self._status(order)
            if status == "Прийнято" or status == "Очікує матеріали":
                queue.append(order)

        queue.sort(key=self._queuePriority)
        return queue

    def _queuePriority(self, order):
        priority = 1
        if order.isUrgent:
            priority = 0

        # Спочатку порівнюється пріоритет, потім бажаний термін.
        return (priority, order.desiredDeadline)

    def startOrder(self, order):
        status = self._status(order)
        if status != "Прийнято" and status != "Очікує матеріали":
            return False

        # Норми витрати зберігаються за номером замовлення:
        # storage["materialRequirements"][order.orderId] = [(material, quantity)]
        if "materialRequirements" not in self._storage:
            raise ValueError("У сховищі не задано потреби в матеріалах.")

        requirements = self._storage["materialRequirements"]
        if order.orderId not in requirements:
            raise ValueError("Для замовлення не задано потреби в матеріалах.")

        # Однаковий матеріал може зустрітися в кількох позиціях.
        totals = {}
        for material, quantity in requirements[order.orderId]:
            quantity = self._positiveDecimal(quantity)
            if quantity is None:
                return False

            materialKey = id(material)
            if materialKey in totals:
                totals[materialKey][1] += quantity
            else:
                totals[materialKey] = [material, quantity]

        for material, quantity in totals.values():
            if not material.checkAvailability(quantity):
                if status == "Прийнято":
                    order.changeStatus("Очікує матеріали")
                return False

        return order.changeStatus("В роботі")

    def completeOrder(self, order):
        if self._status(order) != "В роботі":
            return False

        # Дату готовності та сповіщення обробляє клас Order.
        return order.changeStatus("Готово")

    def registerMaterialUsage(self, order, material, quantity, operationId=None):
        quantity = self._positiveDecimal(quantity)
        if quantity is None:
            return False

        # Спільні ключі операцій захищають від повторного списання.
        if "usageOperations" not in self._storage:
            self._storage["usageOperations"] = {}
        operations = self._storage["usageOperations"]

        if operationId is not None:
            if not isinstance(operationId, str):
                return False
            if operationId.strip() == "":
                return False

            if operationId in operations:
                previous = operations[operationId]
                if previous["order"] is not order:
                    return False
                if previous["material"] is not material:
                    return False
                if previous["quantity"] != quantity:
                    return False
                return True

        if self._status(order) != "В роботі":
            return False
        if not material.checkAvailability(quantity):
            order.changeStatus("Очікує матеріали")
            return False

        from ..inventory.material_usage import MaterialUsage

        usage = MaterialUsage(order=order, material=material, quantity=quantity)
        if not usage.validateQuantity():
            return False
        if not material.writeOff(quantity):
            order.changeStatus("Очікує матеріали")
            return False

        self._storage["usages"].append(usage)
        if operationId is not None:
            operations[operationId] = {
                "order": order,
                "material": material,
                "quantity": quantity
            }
        return True
