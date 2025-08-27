from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt
import pytest
from django.core.mail import send_mail
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def expired_token():
    payload = {
        "user_id": 1,
        "exp": datetime.now(UTC) - timedelta(seconds=10),
    }
    token = jwt.encode(payload, "secret_key", algorithm="HS256")
    return token


send_mail_mock = Mock(return_value=True)
