from datetime import datetime
from .employee import Employee


class Receptionist(Employee):
    PERMISSIONS = ["createOrder", "recordPayment", "issueOrder"]

    def hasPermission(self, action):
        return action in self.PERMISSIONS

    def createOrder(self, orderId, client, service, quantity, desiredDeadline, isUrgent=False):
        if client is None or service is None:
            raise ValueError("Потрібно вказати клієнта та послугу.")
        if not isinstance(orderId, str) or not orderId.strip():
            raise ValueError("Вкажіть номер замовлення.")
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("Кількість має бути додатним цілим числом.")
        if not isinstance(desiredDeadline, datetime):
            raise ValueError("Бажаний термін має містити дату та час.")
        if type(isUrgent) is not bool:
            raise ValueError("Терміновість має бути логічним значенням.")

        from ..orders.order import Order

        order = Order(
            orderId=orderId,
            service=service,
            quantity=quantity,
            desiredDeadline=desiredDeadline,
            isUrgent=isUrgent,
            clientId=getattr(client, "clientId", None),
            receptionistId=self._employeeId,
        )
        client.addOrder(order)
        self._storage["orders"].append(order)
        return order

    def recordPayment(self, paymentId, order, amount, paymentMethod):
        if self._status(order) != "Готово":
            return False

        amount = self._positiveDecimal(amount)
        if amount is None:
            return False
        if amount != order.getTotalPrice():
            return False
        if not isinstance(paymentMethod, str):
            return False
        if paymentMethod.strip() == "":
            return False

        for payment in self._storage["payments"]:
            if payment.orderId == order.orderId:
                return False
            if payment.paymentId == paymentId:
                return False

        from ..orders.payment import Payment

        payment = Payment(
            paymentId=paymentId,
            orderId=order.orderId,
            amount=amount,
            paymentMethod=paymentMethod.strip()
        )
        if not payment.confirmPayment(order.getTotalPrice(), order.getStatus()):
            return False
        if not payment.isPaid():
            return False

        self._storage["payments"].append(payment)
        return True

    def issueOrder(self, order):
        if self._status(order) != "Готово":
            return False

        isPaid = False
        for payment in self._storage["payments"]:
            if payment.orderId == order.orderId and payment.isPaid():
                isPaid = True
                break

        if not order.canBeIssued(isPaid):
            return False
        from ..orders.order import OrderStatus
        return order.changeStatus(OrderStatus.issued)
