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

def test_service_creation_and_info():
    service = Service(1, "Друк фото 10х15", "15.50", "шт.", requiresMaterials=True)
    assert service.serviceId == 1
    assert service.name == "Друк фото 10х15"
    assert service.measurementUnit == "шт."
    assert service.requiresMaterials is True
    assert service.getTariff() == Decimal("15.50")
    assert service.getServiceInfo() == "Друк фото 10х15 — 15.50 грн / шт."


def test_service_invalid_initialization():
    with pytest.raises(ValueError):
        Service(1, "Фото", 0, "шт.")
    with pytest.raises(ValueError):
        Service(1, "   ", 100, "шт.")
    with pytest.raises(ValueError):
        Service(1, "Фото", 100, "шт.", requiresMaterials="yes")  # type: ignore


def test_service_update_price():
    service = Service(1, "Фотокнига", 500, "шт.")
    assert service.updatePrice(650) is True
    assert service.getTariff() == Decimal("650")
    assert service.updatePrice(-50) is False
    assert service.getTariff() == Decimal("650")


def test_order_standard_price_calculation():
    service = Service(1, "Друк фото", "12.00", "шт.")
    deadline = datetime.now() + timedelta(days=2)
    order = Order("ORD-001", service, quantity=10, desiredDeadline=deadline, isUrgent=False)

    assert order.calculateBasePrice() == Decimal("120.00")
    assert order.getTotalPrice() == Decimal("120.00")
    assert order.getStatus() == OrderStatus.accepted


def test_order_urgent_markup_25_percent():
    service = Service(2, "Портретна зйомка", "1000.00", "год.")
    deadline = datetime.now() + timedelta(hours=5)
    order = Order("ORD-002", service, quantity=2, desiredDeadline=deadline, isUrgent=True)

    assert order.calculateBasePrice() == Decimal("2000.00")
    assert order.getTotalPrice() == Decimal("2500.00")


def test_order_set_urgency_toggle():
    service = Service(3, "Реставрація фото", "200.00", "шт.")
    deadline = datetime.now() + timedelta(days=1)
    order = Order("ORD-003", service, quantity=1, desiredDeadline=deadline, isUrgent=False)

    assert order.getTotalPrice() == Decimal("200.00")
    order.setUrgency(True)
    assert order.isUrgent is True
    assert order.getTotalPrice() == Decimal("250.00")


def test_order_status_lifecycle_and_issue_check():
    service = Service(1, "Друк фото", "20.00", "шт.")
    order = Order("ORD-004", service, 5, datetime.now() + timedelta(days=1))

    assert order.changeStatus(OrderStatus.inProgress) is True
    assert order.changeStatus(OrderStatus.ready) is True
    assert order.completedAt is not None

    assert order.canBeIssued(isPaid=False) is False
    assert order.canBeIssued(isPaid=True) is True

    assert order.changeStatus(OrderStatus.issued) is True
    assert order.getStatus() == OrderStatus.issued


def test_payment_confirmation_success():
    payment = Payment(101, "ORD-004", "100.00", "Картка")
    assert payment.isPaid() is False
    assert "Очікує підтвердження" in payment.getPaymentDetails()

    result = payment.confirmPayment(expectedAmount="100.00", orderStatus=OrderStatus.ready)
    assert result is True
    assert payment.isPaid() is True
    assert payment.paymentDate is not None
    assert "Підтверджено" in payment.getPaymentDetails()


def test_payment_invalid_amount_on_creation():
    with pytest.raises(ValueError):
        Payment(102, "ORD-005", 0, "Готівка")


def test_notification_ready_and_send():
    notif = Notification(1, "ORD-004", clientId=10)
    assert notif.getStatus() is False

    notif.generateOrderReadyMessage("ORD-004", Decimal("250.00"))
    assert "ORD-004" in notif.messageText
    assert "250.00 грн" in notif.messageText

    assert notif.send() is True
    assert notif.getStatus() is True
    assert notif.send() is False


def test_notification_shortage_message():
    notif = Notification(2, "ORD-006", clientId=11)
    notif.generateShortageMessage("ORD-006", "Фотопапір глянцевий А4")
    assert "Фотопапір глянцевий А4" in notif.messageText
    assert notif.send() is True