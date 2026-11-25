
import json
import os
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

from photostudio.employees.employee import Employee
from photostudio.employees.receptionist import Receptionist
from photostudio.employees.photographer import Photographer
from photostudio.employees.administrator import Administrator
from photostudio.employees.client import Client

from photostudio.orders.order import Order, OrderStatus
from photostudio.orders.service import Service
from photostudio.orders.payment import Payment
from photostudio.orders.notification import Notification

from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.inventory.material_usage import MaterialUsage
from photostudio.inventory.daily_report import DailyReport


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "studio_data.json"
)

# Дозволені класи для відновлення з JSON
CLASSES = {
    cls.__name__: cls
    for cls in (
        Receptionist,
        Photographer,
        Administrator,
        Client,
        Order,
        Service,
        Payment,
        Notification,
        PhotoMaterial,
        MaterialUsage,
        DailyReport,
    )
}


# ---------- ПЕРЕТВОРЕННЯ В JSON ----------

def serializeData(storage, materialNorms):
    nodes = {}
    references = {}

    def encode(value):
        if value is None or type(value) in (str, int, float, bool):
            return value

        if isinstance(value, Decimal):
            return {"$decimal": str(value)}

        if isinstance(value, datetime):
            return {"$datetime": value.isoformat()}

        if isinstance(value, date):
            return {"$date": value.isoformat()}

        if isinstance(value, OrderStatus):
            return {"$status": value.name}

        # Повторні посилання зберігаємо через ID вузла
        objectId = id(value)

        if objectId in references:
            return {"$ref": references[objectId]}

        reference = str(len(references) + 1)
        references[objectId] = reference

        if isinstance(value, list):
            nodes[reference] = {
                "kind": "list",
                "items": [encode(item) for item in value]
            }

        elif isinstance(value, tuple):
            nodes[reference] = {
                "kind": "tuple",
                "items": [encode(item) for item in value]
            }

        elif isinstance(value, dict):
            nodes[reference] = {
                "kind": "dict",
                "items": [
                    [encode(key), encode(item)]
                    for key, item in value.items()
                ]
            }

        elif type(value).__name__ in CLASSES and (
            type(value) is CLASSES[type(value).__name__]
        ):
            nodes[reference] = {
                "kind": "object",
                "class": type(value).__name__,
                "state": {
                    key: encode(item)
                    for key, item in vars(value).items()
                }
            }

        else:
            raise TypeError(
                f"Неможливо зберегти об'єкт типу {type(value).__name__}."
            )

        return {"$ref": reference}

    root = encode({
        "storage": storage,
        "materialNorms": materialNorms
    })

    return {
        "version": 1,
        "root": root,
        "nodes": nodes
    }


# ---------- ВІДНОВЛЕННЯ З JSON ----------

def deserializeData(data):
    if data.get("version") != 1:
        raise ValueError("Непідтримувана версія файлу даних.")

    nodes = data["nodes"]
    restored = {}

    def decode(value):
        if not isinstance(value, dict):
            return value

        if "$decimal" in value:
            return Decimal(value["$decimal"])

        if "$datetime" in value:
            return datetime.fromisoformat(value["$datetime"])

        if "$date" in value:
            return date.fromisoformat(value["$date"])

        if "$status" in value:
            return OrderStatus[value["$status"]]

        reference = value["$ref"]

        if reference in restored:
            return restored[reference]

        node = nodes[reference]
        kind = node["kind"]

        if kind == "list":
            result = []
            restored[reference] = result
            result.extend(decode(item) for item in node["items"])
            return result

        if kind == "dict":
            result = {}
            restored[reference] = result

            for key, item in node["items"]:
                result[decode(key)] = decode(item)

            return result

        if kind == "tuple":
            result = tuple(
                decode(item) for item in node["items"]
            )
            restored[reference] = result
            return result

        if kind == "object":
            className = node["class"]

            if className not in CLASSES:
                raise ValueError(
                    f"Невідомий клас у JSON: {className}"
                )

            cls = CLASSES[className]

            # Відновлюємо стан без повторного створення
            # замовлень, платежів і списань матеріалів
            result = object.__new__(cls)
            restored[reference] = result

            result.__dict__.update({
                key: decode(item)
                for key, item in node["state"].items()
            })

            return result

        raise ValueError("Невідомий тип даних у JSON.")

    root = decode(data["root"])
    storage = root["storage"]
    materialNorms = root["materialNorms"]

    # Відновлюємо лічильники автоматичних ID
    usages = storage.get("usages", [])
    MaterialUsage._next_usage_id = (
        max((usage.usageId for usage in usages), default=0) + 1
    )

    return storage, materialNorms


# ---------- ЗБЕРЕЖЕННЯ У ФАЙЛ ----------

def saveData(storage, materialNorms, filePath=DATA_FILE):
    path = Path(filePath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = serializeData(storage, materialNorms)

    # Спочатку записуємо тимчасовий файл
    temporaryPath = path.with_suffix(".tmp")

    try:
        with temporaryPath.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        # Замінюємо основний файл лише після запису
        os.replace(temporaryPath, path)

    finally:
        if temporaryPath.exists():
            temporaryPath.unlink()


# ---------- ЗАВАНТАЖЕННЯ З ФАЙЛУ ----------

def loadData(filePath=DATA_FILE):
    path = Path(filePath)

    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return deserializeData(data)

    except (OSError, ValueError, TypeError, KeyError) as error:
        raise RuntimeError(
            f"Не вдалося завантажити дані: {error}"
        ) from error
