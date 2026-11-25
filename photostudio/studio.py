from decimal import Decimal, InvalidOperation
from photostudio.employees.photographer import Photographer
from photostudio.orders.notification import Notification
from photostudio.employees.receptionist import Receptionist
from datetime import date
from photostudio.employees.administrator import Administrator
from photostudio.storage import saveData, loadData


class Studio:
    def __init__(self):
        # Спільні дані для всіх працівників
        self.storage = {
            "employees": [],
            "clients": [],
            "services": [],
            "orders": [],
            "materials": [],
            "payments": [],
            "notifications": [],
            "usages": [],
            "materialRequirements": {},
            "usageOperations": {}
        }

        # Норми витрат матеріалів для кожної послуги
        self.materialNorms = {}

    # ---------- ДОДАВАННЯ ОБ'ЄКТІВ ----------

    def addEmployee(self, employee):
        employeeId = employee._employeeId

        if self.getEmployee(employeeId) is not None:
            raise ValueError("Працівник із таким ID уже існує.")

        # Працівники повинні використовувати спільне сховище
        employee._storage = self.storage
        self.storage["employees"].append(employee)

    def addClient(self, client):
        if self.getClient(client.clientId) is not None:
            raise ValueError("Клієнт із таким ID уже існує.")

        self.storage["clients"].append(client)

    def addService(self, service):
        if self.getService(service.serviceId) is not None:
            raise ValueError("Послуга з таким ID уже існує.")

        self.storage["services"].append(service)

    def addMaterial(self, material):
        if self.getMaterial(material.materialId) is not None:
            raise ValueError("Матеріал із таким ID уже існує.")

        self.storage["materials"].append(material)

    # ---------- ПОШУК ОБ'ЄКТІВ ----------

    def getEmployee(self, employeeId):
        for employee in self.storage["employees"]:
            if employee._employeeId == employeeId:
                return employee
        return None

    def getClient(self, clientId):
        for client in self.storage["clients"]:
            if client.clientId == clientId:
                return client
        return None

    def getService(self, serviceId):
        for service in self.storage["services"]:
            if service.serviceId == serviceId:
                return service
        return None

    def getMaterial(self, materialId):
        for material in self.storage["materials"]:
            if material.materialId == materialId:
                return material
        return None

    def getOrder(self, orderId):
        for order in self.storage["orders"]:
            if order.orderId == orderId:
                return order
        return None

    # ---------- ГЕНЕРАЦІЯ ID ----------

    def generateOrderId(self):
        numbers = []

        for order in self.storage["orders"]:
            orderId = order.orderId

            if orderId.startswith("ORD"):
                suffix = orderId[3:]
                if suffix.isdigit():
                    numbers.append(int(suffix))

        nextId = max(numbers, default=0) + 1
        return f"ORD{nextId:03d}"

    def generatePaymentId(self):
        existing = [
            payment.paymentId
            for payment in self.storage["payments"]
        ]

        return max(existing, default=0) + 1

    def generateNotificationId(self):
        existing = [
            notification.notificationId
            for notification in self.storage["notifications"]
        ]

        return max(existing, default=0) + 1

    # ---------- НОРМАТИВИ МАТЕРІАЛІВ ----------

    def setMaterialNorm(self, serviceId, materialId, quantity):
        service = self.getService(serviceId)
        if service is None:
            raise ValueError("Послугу не знайдено.")

        if not service.requiresMaterials:
            raise ValueError("Для цієї послуги матеріали не потрібні.")

        if self.getMaterial(materialId) is None:
            raise ValueError("Матеріал не знайдено.")

        try:
            if isinstance(quantity, bool):
                raise ValueError
            quantity = Decimal(str(quantity))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Некоректна кількість матеріалу.")

        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("Норма має бути додатним числом.")

        if serviceId not in self.materialNorms:
            self.materialNorms[serviceId] = {}

        self.materialNorms[serviceId][materialId] = quantity

    def calculateMaterialRequirements(self, order):
        serviceId = order.service.serviceId

        if not order.service.requiresMaterials:
            self.storage["materialRequirements"][order.orderId] = []
            return []

        if serviceId not in self.materialNorms:
            raise ValueError(
                "Для послуги не встановлено нормативи матеріалів."
            )

        requirements = []
        for materialId, norm in self.materialNorms[serviceId].items():
            material = self.getMaterial(materialId)
            if material is None:
                raise ValueError("Матеріал із нормативу не знайдено.")

            requiredQuantity = norm * order.quantity
            requirements.append((material, requiredQuantity))

        if not requirements:
            raise ValueError("Для послуги немає норм матеріалів.")

        self.storage["materialRequirements"][order.orderId] = requirements

        return requirements

    
    # ---------- СТВОРЕННЯ ЗАМОВЛЕННЯ ----------

    def createOrder(
        self,
        receptionistId,
        clientId,
        serviceId,
        quantity,
        desiredDeadline,
        isUrgent=False
    ):
        receptionist = self.getEmployee(receptionistId)
        client = self.getClient(clientId)
        service = self.getService(serviceId)

        if receptionist is None or not receptionist.hasPermission("createOrder"):
            raise ValueError("Приймальника не знайдено або немає прав.")

        if client is None:
            raise ValueError("Клієнта не знайдено.")

        if service is None:
            raise ValueError("Послугу не знайдено.")

        if service.requiresMaterials and not self.materialNorms.get(serviceId):
            raise ValueError(
                "Для послуги не встановлено нормативи матеріалів."
            )

        orderId = self.generateOrderId()

        order = receptionist.createOrder(
            orderId,
            client,
            service,
            quantity,
            desiredDeadline,
            isUrgent
        )

        try:
            self.calculateMaterialRequirements(order)
        except Exception:
            self.storage["orders"].remove(order)
            raise

        client.addOrder(order)

        return order



    # ---------- РОБОТА ФОТОГРАФА ----------

    def startOrder(self, photographerId, orderId):
        photographer = self.getEmployee(photographerId)
        order = self.getOrder(orderId)

        if not isinstance(photographer, Photographer):
            raise ValueError("Фотографа не знайдено.")

        if order is None:
            raise ValueError("Замовлення не знайдено.")

        if not photographer.hasPermission("startOrder"):
            raise ValueError("Працівник не має відповідних прав.")

        if not photographer.startOrder(order):
            return False

        # Закріплюємо фотографа за замовленням
        order.assignPhotographer(photographerId)

        return True

    def registerMaterialUsage(
        self,
        photographerId,
        orderId,
        materialId,
        quantity,
        operationId=None
    ):
        photographer = self.getEmployee(photographerId)
        order = self.getOrder(orderId)
        material = self.getMaterial(materialId)

        if not isinstance(photographer, Photographer):
            raise ValueError("Фотографа не знайдено.")

        if order is None:
            raise ValueError("Замовлення не знайдено.")

        if material is None:
            raise ValueError("Матеріал не знайдено.")

        if not photographer.hasPermission("registerMaterialUsage"):
            raise ValueError("Працівник не має відповідних прав.")

        # Матеріали може списувати лише призначений фотограф
        if order.photographerId != photographerId:
            raise ValueError("Замовлення закріплено за іншим фотографом.")

        return photographer.registerMaterialUsage(
            order,
            material,
            quantity,
            operationId=operationId
        )


    
    # ---------- ЗАВЕРШЕННЯ ЗАМОВЛЕННЯ ----------

    def completeOrder(self, photographerId, orderId):
        photographer = self.getEmployee(photographerId)
        order = self.getOrder(orderId)

        if not isinstance(photographer, Photographer):
            raise ValueError("Фотографа не знайдено.")

        if order is None:
            raise ValueError("Замовлення не знайдено.")

        if not photographer.hasPermission("completeOrder"):
            raise ValueError("Працівник не має відповідних прав.")

        if order.photographerId != photographerId:
            raise ValueError("Замовлення закріплено за іншим фотографом.")

        # Завершення роботи фотографом
        if not photographer.completeOrder(order):
            return False

        # Створення сповіщення про готовність
        notification = Notification(
            notificationId=self.generateNotificationId(),
            orderId=orderId,
            clientId=order.clientId
        )

        notification.generateOrderReadyMessage(
            orderId,
            order.getTotalPrice()
        )

        if not notification.send():
            raise RuntimeError("Не вдалося надіслати сповіщення.")

        self.storage["notifications"].append(notification)

        return True



    # ---------- ОПЛАТА ТА ВИДАЧА ЗАМОВЛЕННЯ ----------

    def recordPayment(self, receptionistId, orderId, amount, paymentMethod):
        receptionist = self.getEmployee(receptionistId)
        order = self.getOrder(orderId)

        if not isinstance(receptionist, Receptionist):
            raise ValueError("Приймальника не знайдено.")

        if order is None:
            raise ValueError("Замовлення не знайдено.")

        if not receptionist.hasPermission("recordPayment"):
            raise ValueError("Працівник не має прав на приймання оплати.")

        # Забороняємо повторну оплату одного замовлення
        for payment in self.storage["payments"]:
            if payment.orderId == orderId:
                return False

        paymentId = self.generatePaymentId()

        return receptionist.recordPayment(
            paymentId,
            order,
            amount,
            paymentMethod
        )

    def issueOrder(self, receptionistId, orderId):
        receptionist = self.getEmployee(receptionistId)
        order = self.getOrder(orderId)

        if not isinstance(receptionist, Receptionist):
            raise ValueError("Приймальника не знайдено.")

        if order is None:
            raise ValueError("Замовлення не знайдено.")

        if not receptionist.hasPermission("issueOrder"):
            raise ValueError("Працівник не має прав на видачу замовлень.")

        # Перевіряємо наявність підтвердженої оплати
        isPaid = any(
            payment.orderId == orderId and payment.isPaid()
            for payment in self.storage["payments"]
        )

        if not order.canBeIssued(isPaid):
            return False

        return receptionist.issueOrder(order)


    # ---------- РОБОТА АДМІНІСТРАТОРА ----------

    def replenishMaterial(self, administratorId, materialId, quantity):
        administrator = self.getEmployee(administratorId)
        material = self.getMaterial(materialId)

        if not isinstance(administrator, Administrator):
            raise ValueError("Адміністратора не знайдено.")

        if material is None:
            raise ValueError("Матеріал не знайдено.")

        if not administrator.hasPermission("replenishMaterial"):
            raise ValueError("Недостатньо прав.")

        return administrator.replenishMaterial(material, quantity)

    def generateDailyReport(self, administratorId, reportDate):
        administrator = self.getEmployee(administratorId)

        if not isinstance(administrator, Administrator):
            raise ValueError("Адміністратора не знайдено.")

        if not administrator.hasPermission("generateDailyReport"):
            raise ValueError("Недостатньо прав.")

        if not isinstance(reportDate, date):
            raise ValueError("Некоректна дата звіту.")

        return administrator.generateDailyReport(reportDate)

    # ---------- АВТОРИЗАЦІЯ ----------

    def login(self, login, password):
        if not isinstance(login, str) or not isinstance(password, str):
            raise ValueError("Логін і пароль мають бути рядками.")

        for employee in self.storage["employees"]:
            if employee.getLogin() == login:
                if employee.verifyPassword(password):
                    return employee

                raise ValueError("Неправильний логін або пароль.")

        raise ValueError("Неправильний логін або пароль.")

    def save(self):
        saveData(self.storage, self.materialNorms)

    def load(self):
        result = loadData()

        if result is not None:
            self.storage, self.materialNorms = result
