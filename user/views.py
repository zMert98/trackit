import os

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from trackit import settings
from user.permissions import IsNotAuthentication
from user.serializer import (ResetPasswordRequestSerializer,
                             ResetPasswordSerializer, UserRegisterSerializer)
from user.tasks import send_reset_password_email


class RegisterView(CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [IsNotAuthentication]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        username = response.data.get("username", "пользователь")
        response.data = {
            "message": f"Пользователь {username} успешно зарегистрирован!",
            "user": response.data,
        }
        return response


class RequestPasswordReset(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"user": self.request.user}
        )
        serializer.is_valid(raise_exception=True)
        token = serializer.save()
        reset_url = f"http://localhost:8000/api/v1/user/{os.environ['PASSWORD_RESET_BASE_URL']}{token}"

        send_reset_password_email.delay(reset_url, serializer.validated_data.get("email"))

        return Response(
            {"success": "Мы отправили вам ссылку для сброса пароля"},
            status=status.HTTP_200_OK,
        )


class ResetPassword(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request, token):
        serizalizer = self.serializer_class(data=request.data, context={"token": token})
        serizalizer.is_valid(raise_exception=True)
        serizalizer.save()

        return Response({"success": "Password updated"})
