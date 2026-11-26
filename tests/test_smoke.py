import importlib
import runpy
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from photostudio.employees.client import Client
from photostudio.employees.receptionist import Receptionist
from photostudio.inventory.photo_material import PhotoMaterial
from photostudio.orders.order import OrderStatus
from photostudio.orders.service import Service
from photostudio.storage import loadData, saveData
from photostudio.studio import Studio


@pytest.fixture
def smoke_studio():
    studio = Studio()
    studio.addEmployee(
        Receptionist(1, "Тестовий приймальник", "reception", "1234", "0501111111", studio.storage)
    )
    studio.addClient(Client(1, "Анна", "Тестова", "0671111111"))
    studio.addService(Service(1, "Друк фото", "10.00", "шт.", requiresMaterials=True))
    studio.addMaterial(PhotoMaterial(1, "Фотопапір", 100, "шт.", 10))
    studio.setMaterialNorm(1, 1, 2)
    return studio


def test_application_startup(monkeypatch, capsys):
    def load_startup_data(studio):
        studio.addEmployee(
            Receptionist(1, "Тестовий приймальник", "reception", "1234", "0501111111", studio.storage)
        )

    monkeypatch.setattr(Studio, "load", load_startup_data)
    monkeypatch.setattr(Studio, "save", lambda self: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "0")

    main_path = Path(__file__).resolve().parents[1] / "main.py"
    runpy.run_path(str(main_path), run_name="__main__")

    assert "Дані збережено. До побачення!" in capsys.readouterr().out


def test_studio_initialization(smoke_studio):
    assert isinstance(smoke_studio, Studio)
    assert set(smoke_studio.storage) >= {
        "employees",
        "clients",
        "services",
        "orders",
        "materials",
        "payments",
        "notifications",
        "usages",
    }


def test_basic_data_registration(smoke_studio):
    assert smoke_studio.getEmployee(1) is not None
    assert smoke_studio.getClient(1) is not None
    assert smoke_studio.getService(1) is not None
    assert smoke_studio.getMaterial(1) is not None
    assert smoke_studio.materialNorms == {1: {1: Decimal("2")}}


def test_create_order_smoke(smoke_studio):
    deadline = datetime(2030, 1, 1, 12)
    order = smoke_studio.createOrder(1, 1, 1, 3, deadline)

    assert order.orderId == "ORD001"
    assert order.getStatus() == OrderStatus.accepted
    assert smoke_studio.storage["orders"] == [order]


def test_save_load_smoke(smoke_studio, tmp_path, monkeypatch):
    order = smoke_studio.createOrder(
        1,
        1,
        1,
        3,
        datetime(2030, 1, 1, 12),
    )
    data_file = tmp_path / "smoke_studio_data.json"
    studio_module = importlib.import_module("photostudio.studio")

    monkeypatch.setattr(
        studio_module,
        "saveData",
        lambda storage, norms: saveData(storage, norms, data_file),
    )
    monkeypatch.setattr(
        studio_module,
        "loadData",
        lambda: loadData(data_file),
    )

    smoke_studio.save()
    assert data_file.exists()

    restored = Studio()
    restored.load()

    restored_order = restored.getOrder(order.orderId)
    assert restored_order is not None
    assert restored.getClient(1) is not None