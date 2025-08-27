from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from tasks.models import Tasks


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="testuser", password="123")


@pytest.fixture
def user1(db):
    return get_user_model().objects.create_user(username="testuser1", password="123")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tag1():
    return "тег1"


@pytest.fixture
def tag2():
    return "тег2"

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    fake_redis = MagicMock()
    monkeypatch.setattr("tasks.views.get_redis_connection", fake_redis)
    yield fake_redis

@pytest.fixture
def task_data(tag1, tag2):
    data = {
        "name": "Пример задачи",
        "description": "Описание задачи для демонстрации",
        "items": [
            {
                "name": "Создать проект",
                "description": "Настроить структуру проекта и базовый функционал",
                "status": "process",
                "tags_input": [tag1, tag2],
                "planned_date": "2025-01-01",
            }
        ],
    }
    return data, [tag1, tag2]


@pytest.fixture
def task_data_many_items(tag1, tag2):
    data = {
        "name": "Задача с несколькими элементами",
        "description": "Пример задачи с несколькими элементами",
        "items": [
            {
                "name": "Элемент 1",
                "description": "Описание элемента 1",
                "status": "process",
                "tags_input": [tag1, tag2],
                "planned_date": "2025-01-01",
            },
            {
                "name": "Элемент 2",
                "description": "Описание элемента 2",
                "status": "process",
                "tags_input": ["тег3", "тег4"],
                "planned_date": "2025-01-02",
            },
            {
                "name": "Элемент 3",
                "description": "Описание элемента 3",
                "status": "process",
                "tags_input": ["тег5", "тег6"],
                "planned_date": "2025-01-03",
            },
        ],
    }
    return data


@pytest.fixture
def task_data_many_task():
    tasks = [
        {
            "name": "Задача 1",
            "description": "Описание задачи 1",
            "items": [
                {
                    "name": "Подзадача 1",
                    "description": "Описание подзадачи",
                    "status": "process",
                    "tags_input": ["тег1", "тег2"],
                    "planned_date": "2025-01-01",
                }
            ],
        },
        {
            "name": "Задача 2",
            "description": "Описание задачи 2",
            "items": [
                {
                    "name": "Подзадача 2",
                    "description": "Описание подзадачи",
                    "status": "process",
                    "tags_input": ["тег3", "тег4"],
                    "planned_date": "2025-01-02",
                }
            ],
        },
    ]
    return tasks
