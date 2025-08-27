from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import serializers

from user.models import PasswordReset


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = self.Meta.model(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, mail):
        try:
            user = get_user_model().objects.get(email__exact=mail)
        except get_user_model().DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")

        self.context["user"] = user
        return mail

    def save(self, **kwargs):
        user = self.context["user"]
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        reset = PasswordReset(email=user.email, token=token)
        reset.save()
        return token


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.RegexField(
        regex=r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
        write_only=True,
        error_messages={
            "invalid": (
                "Пароль должен быть длиной не менее 8 символов и содержать хотя бы одну заглавную букву и символ"
            )
        },
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate_confirm_password(self, confirm_password):
        new_password = self.initial_data.get("new_password")
        if confirm_password != new_password:
            raise serializers.ValidationError("Пароли не совпадают")
        self.context["new_password"] = new_password
        return confirm_password

    def validate(self, attrs):
        token = self.context["token"]
        try:
            reset_obj = PasswordReset.objects.get(token=token)
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError("Неверный токен")

        try:
            user = get_user_model().objects.get(email=reset_obj.email)

        except get_user_model().DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")

        self._user = user
        self._reset_obj = reset_obj
        return attrs

    def save(self, **kwargs):
        self._user.set_password(self.context["new_password"])
        self._user.save()
        self._reset_obj.delete()
