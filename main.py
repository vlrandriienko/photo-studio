from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from getpass import getpass
from hashlib import pbkdf2_hmac
from secrets import token_bytes
from uuid import uuid4

from photostudio.studio import Studio
from photostudio.employees.receptionist import Receptionist
from photostudio.employees.photographer import Photographer
from photostudio.employees.administrator import Administrator
from photostudio.employees.client import Client
from photostudio.orders.service import Service
from photostudio.inventory.photo_material import PhotoMaterial


# -------------------- ДОПОМІЖНІ ФУНКЦІЇ --------------------

def field(obj, *names, default=None):
    """Читає властивість із підтримкою camelCase та snake_case."""
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if not callable(value):
                return value
    return default


def call(obj, *method_names):
    """Викликає перший наявний метод без аргументів."""
    for name in method_names:
        method = getattr(obj, name, None)
        if callable(method):
            return method()
    raise AttributeError(f"Не знайдено метод: {', '.join(method_names)}")


def read_text(prompt, *, allow_empty=False):
    while True:
        value = input(prompt).strip()
        if value or allow_empty:
            return value
        print("Значення не може бути порожнім.")


def read_int(prompt, *, minimum=1):
    while True:
        try:
            value = int(read_text(prompt))
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Введіть ціле число не менше {minimum}.")


def read_decimal(prompt, *, minimum=Decimal('0'), strictly_positive=True):
    while True:
        try:
            raw = read_text(prompt).replace(',', '.')
            value = Decimal(raw)
            valid = value.is_finite() and (value > minimum if strictly_positive else value >= minimum)
            if valid:
                return value
        except (InvalidOperation, ValueError):
            pass
        print("Введіть коректну додатну кількість (або нуль, якщо це дозволено).")


def read_date(prompt):
    while True:
        try:
            return date.fromisoformat(read_text(f"{prompt} (РРРР-ММ-ДД): "))
        except ValueError:
            print("Некоректна дата. Наприклад: 2026-12-01")


def read_datetime(prompt):
    while True:
        try:
            return datetime.strptime(
                read_text(f"{prompt} (РРРР-ММ-ДД ГГ:ХХ): "),
                '%Y-%m-%d %H:%M',
            )
        except ValueError:
            print("Некоректні дата або час. Наприклад: 2026-12-01 15:00")


def read_yes_no(prompt):
    while True:
        answer = read_text(f"{prompt} (т/н): ").casefold()
        if answer in ('т', 'так', 'y', 'yes'):
            return True
        if answer in ('н', 'ні', 'n', 'no'):
            return False
        print("Введіть 'т' або 'н'.")


def money(value):
    return f'{value} грн'


def as_status(order):
    status = call(order, 'getStatus', 'get_status')
    return getattr(status, 'value', status)


def order_id(order):
    return field(order, 'orderId', 'order_id')


def employee_id(employee):
    return field(employee, '_employeeId', 'employeeId')


def save(studio):
    studio.save()
    print("Зміни збережено.")


def result_message(result, success, failure='Операцію не виконано.'):
    print(success if result else failure)
    return bool(result)


def show_clients(studio):
    clients = studio.storage['clients']
    if not clients:
        print('Клієнтів поки немає.')
    for client in clients:
        print(f"{client.clientId}: {client.firstName} {client.lastName} | {client.phone}")


def show_services(studio):
    services = studio.storage['services']
    if not services:
        print('Послуг поки немає.')
    for service in services:
        tariff = call(service, 'getTariff', 'get_tariff')
        unit = field(service, 'measurementUnit', 'measurement_unit', default='од.')
        sid = field(service, 'serviceId', 'service_id')
        print(f'{sid}: {service.name} | {money(tariff)}/{unit}')


def show_materials(studio):
    materials = studio.storage['materials']
    if not materials:
        print('Матеріалів поки немає.')
    for material in materials:
        stock = material.getStockQuantity()
        print(f'{material.materialId}: {material.name} | {stock} {material.unit} '
              f'| мінімум: {material.minStock}')


def show_orders(studio, orders=None):
    orders = studio.storage['orders'] if orders is None else orders
    if not orders:
        print('Замовлень немає.')
        return
    for order in orders:
        service = field(order, 'service')
        service_name = field(service, 'name', default='—')
        total = call(order, 'getTotalPrice', 'get_total_price')
        cid = field(order, 'clientId', 'client_id')
        quantity = field(order, 'quantity')
        deadline = field(order, 'desiredDeadline', 'desired_deadline')
        deadline_text = deadline.strftime('%d.%m.%Y %H:%M') if isinstance(deadline, datetime) else str(deadline)
        urgent = field(order, 'isUrgent', 'is_urgent', default=False)
        print(f'{order_id(order)} | клієнт: {cid} | {service_name} × {quantity} | '
              f'{money(total)} | {as_status(order)} | до {deadline_text}'
              f'{" | ТЕРМІНОВО" if urgent else ""}')


def show_notifications(studio, client_id=None):
    found = False
    for notice in studio.storage['notifications']:
        nid = field(notice, 'notificationId', 'notification_id')
        cid = field(notice, 'clientId', 'client_id')
        if client_id is not None and cid != client_id:
            continue
        message = field(notice, 'messageText', 'message_text', default='')
        print(f'#{nid} (клієнт {cid}): {message}')
        found = True
    if not found:
        print('Сповіщень немає.')


def next_numeric_id(objects, *attribute_names):
    ids = [field(obj, *attribute_names, default=0) for obj in objects]
    return max(ids, default=0) + 1


def hash_password(password):
    """PBKDF2-SHA256. Employee.verifyPassword повинен використовувати цей формат."""
    salt = token_bytes(16)
    iterations = 250_000
    digest = pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f'pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}'


def add_employee(studio, *, initial=False):
    if initial:
        cls = Administrator
        print('Створення першого адміністратора.')
    else:
        print('1. Приймальник  2. Фотограф  3. Адміністратор')
        role = read_text('Роль: ')
        cls = {'1': Receptionist, '2': Photographer, '3': Administrator}.get(role)
        if cls is None:
            print('Невідома роль.')
            return
    eid = next_numeric_id(studio.storage['employees'], '_employeeId', 'employeeId')
    name = read_text('ПІБ: ')
    phone = read_text('Телефон: ')
    login = read_text('Логін: ')
    for employee in studio.storage['employees']:
        get_login = getattr(employee, 'getLogin', None)
        if callable(get_login) and get_login() == login:
            print('Такий логін уже існує.')
            return
    while True:
        password = getpass('Пароль (мін. 8 символів): ')
        if len(password) >= 8:
            break
        print('Пароль занадто короткий.')
    employee = cls(
        employeeId=eid,
        fullName=name,
        login=login,
        passwordHash=hash_password(password),
        phone=phone,
        storage=studio.storage,
    )
    studio.addEmployee(employee)
    save(studio)
    print(f'Працівника №{eid} створено.')


# -------------------- ПРИЙМАЛЬНИК --------------------

def register_client(studio):
    client_id = next_numeric_id(studio.storage['clients'], 'clientId')
    client = Client(client_id, read_text('Ім’я: '), read_text('Прізвище: '), read_text('Телефон: '))
    studio.addClient(client)
    save(studio)
    print(f'Клієнта зареєстровано. ID: {client_id}')


def create_order(studio, employee):
    show_clients(studio)
    if not studio.storage['clients']:
        return
    show_services(studio)
    if not studio.storage['services']:
        return
    oid = studio.createOrder(
        receptionistId=employee_id(employee),
        clientId=read_int('ID клієнта: '),
        serviceId=read_int('ID послуги: '),
        quantity=read_int('Кількість: '),
        desiredDeadline=read_datetime('Бажаний термін'),
        isUrgent=read_yes_no('Термінове замовлення?'),
    )
    save(studio)
    print('Замовлення оформлено:')
    show_orders(studio, [oid])


def receive_payment(studio, employee):
    show_orders(studio)
    if not studio.storage['orders']:
        return
    oid = read_text('Номер замовлення: ')
    order = studio.getOrder(oid)
    if order is not None:
        print(f"До сплати: {money(call(order, 'getTotalPrice', 'get_total_price'))}")
    result = studio.recordPayment(
        receptionistId=employee_id(employee),
        orderId=oid,
        amount=read_decimal('Сума платежу: '),
        paymentMethod=read_text('Спосіб оплати (готівка/картка): '),
    )
    if result_message(result, 'Оплату прийнято.'):
        save(studio)


def issue_order(studio, employee):
    show_orders(studio)
    if not studio.storage['orders']:
        return
    result = studio.issueOrder(employee_id(employee), read_text('Номер замовлення: '))
    if result_message(result, 'Замовлення видано.'):
        save(studio)


def receptionist_menu(studio, employee):
    actions = {
        '1': lambda: register_client(studio),
        '2': lambda: show_clients(studio),
        '3': lambda: create_order(studio, employee),
        '4': lambda: show_orders(studio),
        '5': lambda: receive_payment(studio, employee),
        '6': lambda: issue_order(studio, employee),
        '7': lambda: show_notifications(studio),
    }
    menu_loop('ПРИЙМАЛЬНИК', [
        ('1', 'Зареєструвати клієнта'), ('2', 'Переглянути клієнтів'),
        ('3', 'Створити замовлення'), ('4', 'Переглянути замовлення'),
        ('5', 'Прийняти оплату'), ('6', 'Видати замовлення'),
        ('7', 'Переглянути сповіщення'),
    ], actions)


# -------------------- ФОТОГРАФ --------------------

def view_queue(studio, employee):
    show_orders(studio, employee.getOrderQueue())


def start_order(studio, employee):
    view_queue(studio, employee)
    oid = read_text('Номер замовлення: ')
    result = studio.startOrder(employee_id(employee), oid)
    # Нестача матеріалів може змінити статус на «Очікує матеріали».
    save(studio)
    result_message(result, 'Замовлення взято в роботу.',
                   'Почати виконання не вдалося (перевірте статус і матеріали).')


def register_usage(studio, employee):
    show_orders(studio)
    if not studio.storage['orders']:
        return
    oid = read_text('Номер замовлення: ')
    show_materials(studio)
    if not studio.storage['materials']:
        return
    mid = read_int('ID матеріалу: ')
    quantity = read_decimal('Фактично використана кількість: ')
    # Новий ключ на кожну самостійну операцію. Повторне введення
    # є новою операцією, тому користувач не повинен дублювати списання.
    operation_id = uuid4().hex
    result = studio.registerMaterialUsage(
        photographerId=employee_id(employee),
        orderId=oid,
        materialId=mid,
        quantity=quantity,
        operationId=operation_id,
    )
    if result_message(result, 'Витрату матеріалу зареєстровано.'):
        save(studio)


def complete_order(studio, employee):
    show_orders(studio)
    if not studio.storage['orders']:
        return
    result = studio.completeOrder(employee_id(employee), read_text('Номер замовлення: '))
    if result_message(result, 'Замовлення готове, сповіщення сформовано.'):
        save(studio)


def photographer_menu(studio, employee):
    actions = {
        '1': lambda: view_queue(studio, employee),
        '2': lambda: start_order(studio, employee),
        '3': lambda: register_usage(studio, employee),
        '4': lambda: complete_order(studio, employee),
    }
    menu_loop('ФОТОГРАФ', [
        ('1', 'Переглянути чергу'), ('2', 'Почати виконання'),
        ('3', 'Зареєструвати витрату матеріалів'), ('4', 'Завершити замовлення'),
    ], actions)


# -------------------- АДМІНІСТРАТОР --------------------

def add_service(studio):
    sid = next_numeric_id(studio.storage['services'], 'serviceId', 'service_id')
    service = Service(
        service_id=sid,
        name=read_text('Назва послуги: '),
        base_tariff=read_decimal('Тариф: '),
        measurement_unit=read_text('Одиниця послуги (фото/шт.): '),
    )
    studio.addService(service)
    save(studio)
    print(f'Послугу додано. ID: {sid}')
    print('Не забудьте налаштувати нормативи матеріалів для цієї послуги.')


def add_material(studio):
    mid = next_numeric_id(studio.storage['materials'], 'materialId')
    material = PhotoMaterial(
        materialId=mid,
        name=read_text('Назва матеріалу: '),
        stockQuantity=read_decimal('Початковий запас: ', strictly_positive=False),
        unit=read_text('Одиниця матеріалу (шт./л): '),
        minStock=read_decimal('Мінімальний запас: ', strictly_positive=False),
    )
    studio.addMaterial(material)
    save(studio)
    print(f'Матеріал додано. ID: {mid}')


def set_norm(studio):
    show_services(studio)
    if not studio.storage['services']:
        return
    sid = read_int('ID послуги: ')
    show_materials(studio)
    if not studio.storage['materials']:
        return
    mid = read_int('ID матеріалу: ')
    norm = read_decimal('Витрата матеріалу на одну одиницю послуги: ')
    studio.setMaterialNorm(sid, mid, norm)
    save(studio)
    print('Норматив матеріалу встановлено.')


def show_norms(studio):
    if not studio.materialNorms:
        print('Нормативів поки немає.')
        return
    for sid, norms in studio.materialNorms.items():
        service = studio.getService(sid)
        print(f"Послуга {sid}: {field(service, 'name', default='невідома')}")
        for mid, amount in norms.items():
            material = studio.getMaterial(mid)
            print(f"  {field(material, 'name', default=f'матеріал {mid}')}: "
                  f"{amount} {field(material, 'unit', default='од.')}/од. послуги")


def replenish_material(studio, employee):
    show_materials(studio)
    if not studio.storage['materials']:
        return
    mid = read_int('ID матеріалу: ')
    quantity = read_decimal('Кількість поповнення: ')
    result = studio.replenishMaterial(employee_id(employee), mid, quantity)
    if result_message(result, 'Матеріал поповнено.'):
        save(studio)


def daily_report(studio, employee):
    day = read_date('Дата звіту')
    report = studio.generateDailyReport(employee_id(employee), day)
    print(report.getSummary())


def show_employees(studio):
    for employee in studio.storage['employees']:
        print(f'{employee.getProfile()} | {type(employee).__name__}')


def administrator_menu(studio, employee):
    actions = {
        '1': lambda: show_materials(studio),
        '2': lambda: add_material(studio),
        '3': lambda: replenish_material(studio, employee),
        '4': lambda: show_services(studio),
        '5': lambda: add_service(studio),
        '6': lambda: set_norm(studio),
        '7': lambda: show_norms(studio),
        '8': lambda: daily_report(studio, employee),
        '9': lambda: add_employee(studio),
        '10': lambda: show_employees(studio),
    }
    menu_loop('АДМІНІСТРАТОР', [
        ('1', 'Переглянути матеріали'), ('2', 'Додати матеріал'),
        ('3', 'Поповнити матеріал'), ('4', 'Переглянути послуги'),
        ('5', 'Додати послугу'), ('6', 'Встановити норматив матеріалу'),
        ('7', 'Переглянути нормативи'), ('8', 'Сформувати денний звіт'),
        ('9', 'Додати працівника'), ('10', 'Переглянути працівників'),
    ], actions)


# -------------------- МЕНЮ І ЗАПУСК --------------------

def menu_loop(title, options, actions):
    while True:
        print(f'\n========== {title} ==========')
        for key, label in options:
            print(f'{key}. {label}')
        print('0. Вийти з облікового запису')
        choice = read_text('Ваш вибір: ')
        if choice == '0':
            return
        action = actions.get(choice)
        if action is None:
            print('Невідомий пункт меню.')
            continue
        try:
            action()
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError, OSError) as exc:
            print(f'Помилка: {exc}')


def login_menu(studio):
    print('\n=== ВХІД ПРАЦІВНИКА ===')
    login = read_text('Логін: ')
    password = getpass('Пароль: ')
    try:
        employee = studio.login(login, password)
    except (ValueError, AttributeError) as exc:
        print(f'Не вдалося увійти: {exc}')
        return
    print(f'Вітаємо! {employee.getProfile()}')
    if isinstance(employee, Receptionist):
        receptionist_menu(studio, employee)
    elif isinstance(employee, Photographer):
        photographer_menu(studio, employee)
    elif isinstance(employee, Administrator):
        administrator_menu(studio, employee)
    else:
        print('Для цієї ролі немає меню.')


def main():
    studio = Studio()
    try:
        studio.load()
    except (RuntimeError, OSError, ValueError) as exc:
        print(f'Помилка завантаження даних: {exc}')
        print('Програму зупинено, щоб не перезаписати наявні дані.')
        return

    # Новий проєкт: створення першого адміністратора.
    if not studio.storage['employees']:
        print('У системі немає працівників.')
        try:
            add_employee(studio, initial=True)
        except (ValueError, TypeError, AttributeError, OSError, RuntimeError) as exc:
            print(f'Не вдалося створити адміністратора: {exc}')
            return

    while True:
        print('\n========== ФОТОСТУДІЯ ==========')
        print('1. Вхід працівника')
        print('2. Перевірити статус замовлення')
        print('3. Переглянути сповіщення клієнта')
        print('0. Завершити програму')
        choice = read_text('Ваш вибір: ')
        try:
            if choice == '1':
                login_menu(studio)
            elif choice == '2':
                oid = read_text('Номер замовлення: ')
                order = studio.getOrder(oid)
                if order is None:
                    print('Замовлення не знайдено.')
                else:
                    cid = read_int('ID клієнта для підтвердження: ')
                    if field(order, 'clientId', 'client_id') != cid:
                        print('Замовлення не належить цьому клієнту.')
                    else:
                        show_orders(studio, [order])
            elif choice == '3':
                cid = read_int('ID клієнта: ')
                # Для навчального застосунку повідомлення доступні за ID.
                # У реальному застосунку потрібна автентифікація клієнтів.
                if studio.getClient(cid) is None:
                    print('Клієнта не знайдено.')
                else:
                    show_notifications(studio, cid)
            elif choice == '0':
                studio.save()
                print('Дані збережено. До побачення!')
                break
            else:
                print('Некоректний вибір.')
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError, OSError) as exc:
            print(f'Помилка: {exc}')


if __name__ == '__main__':
    main()
