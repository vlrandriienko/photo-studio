import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from photostudio.employees.administrator import Administrator
from photostudio.employees.client import Client
from photostudio.employees.photographer import Photographer
from photostudio.employees.receptionist import Receptionist
from photostudio.inventory.material_usage import MaterialUsage
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.orders.notification import Notification
from photostudio.orders.order import Order, OrderStatus
from photostudio.orders.payment import Payment
from photostudio.orders.service import Service


DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "studio_data.json"

EMPLOYEE_TYPES = {
    "Administrator": Administrator,
    "Photographer": Photographer,
    "Receptionist": Receptionist,
}


def serializeData(storage, materialNorms):
    employees = []
    for employee in storage["employees"]:
        employees.append({
            "employeeId": employee._employeeId,
            "role": type(employee).__name__,
            "fullName": employee._fullName,
            "login": employee.getLogin(),
            "passwordHash": employee.__dict__["_Employee__passwordHash"],
            "phone": employee._phone,
        })

    clients = [
        {
            "clientId": client.clientId,
            "firstName": client.firstName,
            "lastName": client.lastName,
            "phone": client.phone,
        }
        for client in storage["clients"]
    ]

    services = [
        {
            "serviceId": service.serviceId,
            "name": service.name,
            "baseTariff": str(service.getTariff()),
            "measurementUnit": service.measurementUnit,
            "requiresMaterials": service.requiresMaterials,
        }
        for service in storage["services"]
    ]

    materials = [
        {
            "materialId": material.materialId,
            "name": material.name,
            "stockQuantity": str(material.getStockQuantity()),
            "unit": material.unit,
            "minStock": str(material.minStock),
        }
        for material in storage["materials"]
    ]

    orders = []
    for order in storage["orders"]:
        orders.append({
            "orderId": order.orderId,
            "clientId": order.clientId,
            "serviceId": order.service.serviceId,
            "receptionistId": order.__dict__["_Order__receptionistId"],
            "photographerId": order.photographerId,
            "quantity": order.quantity,
            "isUrgent": order.isUrgent,
            "status": order.getStatus().value,
            "createdAt": order.createdAt.isoformat(),
            "desiredDeadline": order.desiredDeadline.isoformat(),
            "completedAt": order.completedAt.isoformat() if order.completedAt else None,
            "unitPrice": str(order.__dict__["_Order__unitPrice"]),
            "basePrice": str(order.__dict__["_Order__basePrice"]),
            "totalPrice": str(order.getTotalPrice()),
        })

    payments = [
        {
            "paymentId": payment.paymentId,
            "orderId": payment.orderId,
            "amount": str(payment.amount),
            "paymentDate": payment.paymentDate.isoformat() if payment.paymentDate else None,
            "paymentMethod": payment.paymentMethod,
            "isConfirmed": payment.isPaid(),
        }
        for payment in storage["payments"]
    ]

    notifications = [
        {
            "notificationId": notification.notificationId,
            "orderId": notification.orderId,
            "clientId": notification.clientId,
            "messageText": notification.messageText,
            "createdAt": notification.createdAt.isoformat(),
            "isSent": notification.getStatus(),
        }
        for notification in storage["notifications"]
    ]

    usages = [
        {
            "usageId": usage.usageId,
            "orderId": usage.order.orderId,
            "materialId": usage.material.materialId,
            "quantity": str(usage.quantity),
            "recordedAt": usage.recordedAt.isoformat(),
        }
        for usage in storage["usages"]
    ]

    serializedNorms = {
        str(serviceId): {
            str(materialId): str(quantity)
            for materialId, quantity in norms.items()
        }
        for serviceId, norms in materialNorms.items()
    }

    requirements = {
        orderId: [
            {
                "materialId": material.materialId,
                "quantity": str(quantity),
            }
            for material, quantity in items
        ]
        for orderId, items in storage["materialRequirements"].items()
    }

    operations = {
        operationId: {
            "orderId": operation["order"].orderId,
            "materialId": operation["material"].materialId,
            "quantity": str(operation["quantity"]),
        }
        for operationId, operation in storage["usageOperations"].items()
    }

    return {
        "employees": employees,
        "clients": clients,
        "services": services,
        "materials": materials,
        "orders": orders,
        "payments": payments,
        "notifications": notifications,
        "usages": usages,
        "materialNorms": serializedNorms,
        "materialRequirements": requirements,
        "usageOperations": operations,
    }


def deserializeData(data):
    requiredCollections = (
        "employees",
        "clients",
        "services",
        "materials",
        "orders",
        "payments",
        "notifications",
        "usages",
        "materialNorms",
        "materialRequirements",
        "usageOperations",
    )
    if not isinstance(data, dict):
        raise ValueError("Корінь JSON має бути об'єктом.")
    if any(key not in data for key in requiredCollections):
        raise ValueError("У JSON відсутня обов'язкова колекція.")

    storage = {
        "employees": [],
        "clients": [],
        "services": [],
        "orders": [],
        "materials": [],
        "payments": [],
        "notifications": [],
        "usages": [],
        "materialRequirements": {},
        "usageOperations": {},
    }

    def uniqueMap(items, idField, collectionName):
        result = {}
        for item in items:
            objectId = item[idField]
            if objectId in result:
                raise ValueError(f"Дубльований ID у колекції {collectionName}: {objectId}.")
            result[objectId] = item
        return result

    employeeRecords = uniqueMap(data["employees"], "employeeId", "employees")
    clientRecords = uniqueMap(data["clients"], "clientId", "clients")
    serviceRecords = uniqueMap(data["services"], "serviceId", "services")
    materialRecords = uniqueMap(data["materials"], "materialId", "materials")
    orderRecords = uniqueMap(data["orders"], "orderId", "orders")
    paymentRecords = uniqueMap(data["payments"], "paymentId", "payments")
    notificationRecords = uniqueMap(data["notifications"], "notificationId", "notifications")
    usageRecords = uniqueMap(data["usages"], "usageId", "usages")

    employees = {}
    for employeeId, record in employeeRecords.items():
        role = record["role"]
        if role not in EMPLOYEE_TYPES:
            raise ValueError(f"Невідома роль працівника: {role}.")
        if not isinstance(record["passwordHash"], str) or not record["passwordHash"].startswith(
            "pbkdf2_sha256$"
        ):
            raise ValueError(f"Некоректний хеш пароля працівника {employeeId}.")

        employee = object.__new__(EMPLOYEE_TYPES[role])
        employee._employeeId = employeeId
        employee._fullName = record["fullName"]
        employee._phone = record["phone"]
        employee._Employee__login = record["login"]
        employee._Employee__passwordHash = record["passwordHash"]
        storage["employees"].append(employee)
        employees[employeeId] = employee

    clients = {}
    for clientId, record in clientRecords.items():
        client = Client(
            clientId=clientId,
            firstName=record["firstName"],
            lastName=record["lastName"],
            phone=record["phone"],
        )
        clients[clientId] = client
        storage["clients"].append(client)

    services = {}
    for serviceId, record in serviceRecords.items():
        service = Service(
            serviceId=serviceId,
            name=record["name"],
            baseTariff=Decimal(record["baseTariff"]),
            measurementUnit=record["measurementUnit"],
            requiresMaterials=record["requiresMaterials"],
        )
        services[serviceId] = service
        storage["services"].append(service)

    materials = {}
    for materialId, record in materialRecords.items():
        material = PhotoMaterial(
            materialId=materialId,
            name=record["name"],
            stockQuantity=Decimal(record["stockQuantity"]),
            unit=record["unit"],
            minStock=Decimal(record["minStock"]),
        )
        materials[materialId] = material
        storage["materials"].append(material)

    orders = {}
    for orderId, record in orderRecords.items():
        serviceId = record["serviceId"]
        if serviceId not in services:
            raise ValueError(f"Послугу {serviceId} для замовлення {orderId} не знайдено.")
        clientId = record["clientId"]
        if clientId not in clients:
            raise ValueError(f"Клієнта {clientId} для замовлення {orderId} не знайдено.")
        receptionistId = record["receptionistId"]
        if receptionistId not in employees:
            raise ValueError(f"Приймальника {receptionistId} для замовлення {orderId} не знайдено.")

        order = Order(
            orderId=orderId,
            service=services[serviceId],
            quantity=record["quantity"],
            desiredDeadline=datetime.fromisoformat(record["desiredDeadline"]),
            isUrgent=record["isUrgent"],
            clientId=clientId,
            receptionistId=receptionistId,
        )
        order.__dict__["_Order__createdAt"] = datetime.fromisoformat(record["createdAt"])
        order.__dict__["_Order__completedAt"] = (
            datetime.fromisoformat(record["completedAt"]) if record["completedAt"] else None
        )
        order.__dict__["_Order__photographerId"] = record["photographerId"]
        order.__dict__["_Order__unitPrice"] = Decimal(record["unitPrice"])
        order.__dict__["_Order__basePrice"] = Decimal(record["basePrice"])
        order.__dict__["_Order__totalPrice"] = Decimal(record["totalPrice"])
        try:
            order.__dict__["_Order__status"] = OrderStatus(record["status"])
        except ValueError as error:
            raise ValueError(f"Невідомий статус замовлення {orderId}.") from error

        clients[clientId].addOrder(order)
        orders[orderId] = order
        storage["orders"].append(order)

    for paymentId, record in paymentRecords.items():
        orderId = record["orderId"]
        if orderId not in orders:
            raise ValueError(f"Замовлення {orderId} для платежу {paymentId} не знайдено.")
        payment = Payment(
            paymentId=paymentId,
            orderId=orderId,
            amount=Decimal(record["amount"]),
            paymentMethod=record["paymentMethod"],
        )
        payment.__dict__["_Payment__paymentDate"] = (
            datetime.fromisoformat(record["paymentDate"]) if record["paymentDate"] else None
        )
        payment.__dict__["_Payment__isConfirmed"] = record["isConfirmed"]
        storage["payments"].append(payment)

    for notificationId, record in notificationRecords.items():
        orderId = record["orderId"]
        clientId = record["clientId"]
        if orderId not in orders or clientId not in clients:
            raise ValueError(f"Некоректні зв'язки сповіщення {notificationId}.")
        notification = Notification(
            notificationId=notificationId,
            orderId=orderId,
            clientId=clientId,
            messageText=record["messageText"],
        )
        notification.__dict__["_Notification__createdAt"] = datetime.fromisoformat(
            record["createdAt"]
        )
        notification.__dict__["_Notification__isSent"] = record["isSent"]
        storage["notifications"].append(notification)

    for usageId, record in usageRecords.items():
        orderId = record["orderId"]
        materialId = record["materialId"]
        if orderId not in orders or materialId not in materials:
            raise ValueError(f"Некоректні зв'язки витрати матеріалу {usageId}.")
        storage["usages"].append(MaterialUsage(
            order=orders[orderId],
            material=materials[materialId],
            quantity=Decimal(record["quantity"]),
            usageId=usageId,
            recordedAt=datetime.fromisoformat(record["recordedAt"]),
        ))

    materialNorms = {}
    for serviceIdText, norms in data["materialNorms"].items():
        serviceId = int(serviceIdText)
        if serviceId not in services:
            raise ValueError(f"Послугу {serviceId} для нормативів не знайдено.")
        storageNorms = {}
        for materialId, quantity in norms.items():
            materialId = int(materialId)
            if materialId not in materials:
                raise ValueError(f"Матеріал {materialId} для нормативу не знайдено.")
            storageNorms[materialId] = Decimal(quantity)
        materialNorms[serviceId] = storageNorms

    for orderId, items in data["materialRequirements"].items():
        if orderId not in orders:
            raise ValueError(f"Замовлення {orderId} для нормативів не знайдено.")
        storage["materialRequirements"][orderId] = [
            (materials[item["materialId"]], Decimal(item["quantity"]))
            for item in items
            if item["materialId"] in materials
        ]
        if len(storage["materialRequirements"][orderId]) != len(items):
            raise ValueError(f"Матеріал для вимог замовлення {orderId} не знайдено.")

    for operationId, record in data["usageOperations"].items():
        orderId = record["orderId"]
        materialId = record["materialId"]
        if orderId not in orders or materialId not in materials:
            raise ValueError(f"Некоректні зв'язки операції списання {operationId}.")
        storage["usageOperations"][operationId] = {
            "order": orders[orderId],
            "material": materials[materialId],
            "quantity": Decimal(record["quantity"]),
        }

    for employee in storage["employees"]:
        employee._storage = storage

    MaterialUsage._next_usage_id = max(
        (usage.usageId for usage in storage["usages"]),
        default=0,
    ) + 1

    return storage, materialNorms


def saveData(storage, materialNorms, filePath=DATA_FILE):
    path = Path(filePath)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporaryPath = path.with_suffix(".tmp")

    try:
        with temporaryPath.open("w", encoding="utf-8") as file:
            json.dump(
                serializeData(storage, materialNorms),
                file,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(temporaryPath, path)
    finally:
        if temporaryPath.exists():
            temporaryPath.unlink()


def loadData(filePath=DATA_FILE):
    path = Path(filePath)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return deserializeData(data)
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise RuntimeError(f"Не вдалося завантажити дані: {error}") from error
