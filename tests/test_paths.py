from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from photostudio.orders import (
    Service,
    Order,
    OrderStatus,
    Payment,
    Notification,
)


@pytest.mark.parametrize(
    "orderId, quantity, isUrgent, expectedTotal, shouldRaise",
    [
        ("", 1, False, None, True),
        ("ORD-10", 0, False, None, True),
        ("ORD-11", 3, False, Decimal("300.00"), False),
        ("ORD-12", 3, True, Decimal("375.00"), False),
    ],
)
def test_order_creation_and_total_paths(orderId, quantity, isUrgent, expectedTotal, shouldRaise):
    service = Service(1, "Студійна зйомка", "100.00", "год.")
    deadline = datetime.now() + timedelta(days=1)

    if shouldRaise:
        with pytest.raises(ValueError):
            Order(orderId, service, quantity, deadline, isUrgent=isUrgent)
    else:
        order = Order(orderId, service, quantity, deadline, isUrgent=isUrgent)
        assert order.getTotalPrice() == expectedTotal


def test_order_validation_type_paths():
    service = Service(1, "Друк", "50.00", "шт.")
    deadline = datetime.now() + timedelta(days=1)

    with pytest.raises(ValueError):
        Order("ORD-13", service, 1, "2026-12-01")  # type: ignore

    with pytest.raises(ValueError):
        Order("ORD-14", service, 1, deadline, isUrgent="так")  # type: ignore

    with pytest.raises(ValueError):
        Order("ORD-15", "Не послуга", 1, deadline)  # type: ignore


def test_set_urgency_paths():
    service = Service(1, "Друк", "100.00", "шт.")
    order = Order("ORD-20", service, 1, datetime.now() + timedelta(days=1))

    order.setUrgency(True)
    assert order.getTotalPrice() == Decimal("125.00")

    order.changeStatus(OrderStatus.inProgress)
    with pytest.raises(ValueError):
        order.setUrgency(False)


def test_order_status_transition_paths():
    service = Service(1, "Друк", "50.00", "шт.")
    order = Order("ORD-30", service, 2, datetime.now() + timedelta(days=1))

    assert order.changeStatus(OrderStatus.ready) is False

    assert order.changeStatus(OrderStatus.awaitingMaterials) is True
    assert order.changeStatus(OrderStatus.inProgress) is True
    assert order.changeStatus(OrderStatus.ready) is True
    assert order.changeStatus(OrderStatus.issued) is True

    assert order.changeStatus(OrderStatus.ready) is False


def test_payment_confirmation_all_paths():
    payment = Payment(501, "ORD-40", "250.00", "Готівка")

    assert payment.confirmPayment("250.00", OrderStatus.inProgress) is False

    assert payment.confirmPayment("200.00", OrderStatus.ready) is False

    assert payment.confirmPayment("250.00", OrderStatus.ready) is True
    assert payment.isPaid() is True

    assert payment.confirmPayment("250.00", OrderStatus.ready) is False


def test_notification_send_paths():
    empty_notif = Notification(10, "ORD-50")
    assert empty_notif.send() is False

    notif = Notification(11, "ORD-50", messageText="Замовлення прийнято")
    assert notif.send() is True

    assert notif.send() is False