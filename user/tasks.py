from celery import shared_task
from django.core.mail import send_mail
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from trackit import settings


@shared_task
def send_reset_password_email(reset_url, validated_data):
    send_mail(
        subject="Восстановление/Изменение пароля",
        message=f"""
    Здравствуйте!

    Вы запросили сброс пароля на сайте TrackIt.

    Чтобы задать новый пароль, перейдите по ссылке ниже:
    {reset_url}

    Если вы не запрашивали сброс, просто проигнорируйте это письмо.

    С уважением, команда TrackIt.
    """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[validated_data],
    )


@shared_task
def clear_blacklist():
    blacklisted_tokens = tuple(BlacklistedToken.objects.all().values_list('token__jti', flat=True))
    outstanding_tokens = OutstandingToken.objects.filter(jti__in=blacklisted_tokens)

    outstanding_tokens.delete()
    BlacklistedToken.objects.all().delete()