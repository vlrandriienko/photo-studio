# Photostudio Management System

Система управління роботою фотостудії.

## Технології
- Python 3.12
- pytest


## Структура проекту
photo-studio/

    photostudio/
        __init__.py
        employees/
            __init__.py
            employee.py           # Аня
            receptionist.py       # Аня
            photographer.py       # Аня
            administrator.py      # Аня
        orders/
            __init__.py
            order.py              # Юля
            service.py            # Юля
            payment.py            # Юля
            notification.py       # Юля
        inventory/
            __init__.py
            client.py             # Віталіна
            photo_material.py     # Віталіна
            material_usage.py     # Віталіна
            daily_report.py       # Віталіна
        studio.py                  # Лєра
        storage.py                 # Лєра
    tests/
        test_employees.py         # Аня
        test_orders.py            # Юля
        test_inventory.py         # Віталіна
        test_integration.py       # Лєра
        test_smoke.py             # Лєра
        test_load_stress.py       # Віталіна
        test_paths.py             # Юля
    main.py                       # Лєра
    requirements.txt
    README.md
    .gitignore
