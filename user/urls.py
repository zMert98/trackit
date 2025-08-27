from django.urls import path

from user.views import RegisterView, RequestPasswordReset, ResetPassword

app_name = "user"

urlpatterns = [
    path("registration/", RegisterView.as_view(), name="trackit-register"),
    path(
        "password-reset-request/",
        RequestPasswordReset.as_view(),
        name="trackit-password-reset-request",
    ),
    path(
        "password-reset/<str:token>/",
        ResetPassword.as_view(),
        name="trackit-password-reset",
    ),
]
