import os
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from user.factory import TaskFactory, UserFactory
from user.models import PasswordReset


@pytest.mark.django_db
class TestPasswordReset:
    ERROR_MESSAGES = {
        "weak_password": "Пароль должен быть длиной не менее 8 символов и содержать хотя бы одну заглавную букву и символ",
        "mismatch": "Пароли не совпадают",
    }

    def setUp(self):
        os.environ["PASSWORD_RESET_BASE_URL"] = "password-reset/"

    def test_password_reset(self, api_client):
        user = UserFactory()

        response = api_client.post(
            "/api/v1/user/password-reset-request/", data={"email": user.email}
        )

        assert response.status_code in [200, 201]
        token = PasswordReset.objects.get(email=user.email).token
        reset_password_url = (
            f'/api/v1/user/{os.getenv("PASSWORD_RESET_BASE_URL")}{token}/'
        )

        response = api_client.post(
            reset_password_url,
            {"new_password": "19952004R@", "confirm_password": "19952004R@"},
        )
        assert response.status_code in [200, 201]
        user.refresh_from_db()
        assert user.check_password("19952004R@")

    @pytest.mark.parametrize(
        "pw1, pw2, field, error_m",
        [
            ("short1@", "short1@", "new_password", ERROR_MESSAGES["weak_password"]),
            # короче 8 символов
            (
                "alllowercase1@",
                "alllowercase1@",
                "new_password",
                ERROR_MESSAGES["weak_password"],
            ),
            # нет заглавных
            (
                "NoSymbol123",
                "NoSymbol123",
                "new_password",
                ERROR_MESSAGES["weak_password"],
            ),
            # нет спецсимвола
            ("NoDigit@!", "NoDigit@!", "new_password", ERROR_MESSAGES["weak_password"]),
            (
                "NoSpecialChar1",
                "NoSpecialChar1",
                "new_password",
                ERROR_MESSAGES["weak_password"],
            ),
            # нет спецсимвола
            (
                "NotEqual1@",
                "NotEqual11@R",
                "confirm_password",
                ERROR_MESSAGES["mismatch"],
            ),
            # не равны
        ],
        ids=[
            "short_password",
            "no_uppercase",
            "no_special",
            "no_digit",
            "no_special_2",
            "mismatch",
        ],
    )
    def test_password_reset_with_invalid_password_fails(
        self, api_client, pw1, pw2, error_m, field
    ):
        user = UserFactory()

        response = api_client.post(
            "/api/v1/user/password-reset-request/", data={"email": user.email}
        )

        assert response.status_code in [200, 201]
        token = PasswordReset.objects.get(email=user.email).token
        reset_password_url = (
            f'/api/v1/user/{os.getenv("PASSWORD_RESET_BASE_URL")}{token}/'
        )

        response = api_client.post(
            reset_password_url, {"new_password": pw1, "confirm_password": pw2}
        )
        assert response.status_code == 400
        assert response.json()[field][0] == error_m


@patch("user.tasks.send_reset_password_email.delay")
@pytest.mark.django_db
class TestEmailSending:
    def test_sending_letters_by_email(self, send_mail_mock, api_client):
        user = UserFactory()

        response = api_client.post(
            "/api/v1/user/password-reset-request/", data={"email": user.email}
        )

        assert response.status_code in [200, 201]
        send_mail_mock.assert_called()
        print(send_mail_mock.call_args.kwargs)
        assert (
            user.email
            in send_mail_mock.call_args.args
        )


@pytest.mark.django_db
class TestUserRegistration:
    def test_registration(self, api_client):
        response = api_client.post(
            "/api/v1/user/registration/",
            data={
                "username": "testuser",
                "email": "testuser@example.com",
                "password": "123456",
            },
        )
        assert response.status_code in [200, 201]
        user = get_user_model().objects.filter(
            username=response.data["user"]["username"]
        )
        assert len(user) > 0


@pytest.mark.django_db
class TestUserAuthorizationAuthentication:
    def test_authentication(self, api_client):
        user = UserFactory()
        user.save()
        response = api_client.get("/api/v1/tasks/")
        assert response.status_code == 401

        response = api_client.post(
            "/api/v1/token/",
            data={"username": user.username, "password": "defaultpassword123"},
        )
        assert response.status_code == 200
        access_token = f"Bearer {response.data['access']}"
        response = api_client.get("/api/v1/tasks/", HTTP_AUTHORIZATION=access_token)
        assert response.status_code == 200

    def test_authorization(self, api_client):
        user = UserFactory()
        task = TaskFactory()
        api_client.force_authenticate(user)
        response = api_client.get(
            f"/api/v1/tasks/{task.id}/", HTTP_ACCEPT="application/json"
        )

        assert response.status_code in [403, 404]
        assert response.json()["detail"] == "No Tasks matches the given query."


@pytest.mark.django_db
class TestJWTToken:
    def test_authentication_with_invalid_access_token(self, api_client):
        response = api_client.get("/api/v1/tasks/")
        assert response.status_code == 401

        invalid_token = f"Bearer invalid_token"

        response = api_client.get("/api/v1/tasks/", HTTP_AUTHORIZATION=invalid_token)
        assert response.status_code == 401
        assert response.data["detail"] == "Given token not valid for any token type"

    def test_authentication_with_expired_token(self, api_client, expired_token):
        response = api_client.get("/api/v1/tasks/", HTTP_AUTHORIZATION=expired_token)
        assert response.status_code == 401

    def test_refresh_token(self, api_client):
        user = UserFactory()
        user.save()

        response = api_client.post(
            "/api/v1/token/",
            data={"username": user.username, "password": "defaultpassword123"},
        )
        assert response.status_code == 200
        refresh_token = response.data["refresh"]
        response = api_client.post(
            "/api/v1/token/refresh/", data={"refresh": refresh_token}
        )

        assert response.status_code == 200
        access_token = f"Bearer {response.data['access']}"
        response = api_client.get("/api/v1/tasks/", HTTP_AUTHORIZATION=access_token)
        assert response.status_code == 200

    def test_refresh_blacklisted_token(self, api_client):
        user = UserFactory()
        user.save()

        response = api_client.post(
            "/api/v1/token/",
            data={"username": user.username, "password": "defaultpassword123"},
        )
        assert response.status_code == 200

        refresh_token = response.data["refresh"]
        response = api_client.post(
            "/api/v1/token/logout/", data={"refresh": refresh_token}
        )
        assert response.status_code == 200

        response = api_client.post(
            "/api/v1/token/refresh/", data={"refresh": refresh_token}
        )
        assert response.status_code == 401
        assert response.data["detail"] == "Token is blacklisted"
