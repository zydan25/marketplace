from django.urls import path

from .auth import SecureLoginView, SecureRegisterView, me


urlpatterns = [
    path("login/", SecureLoginView.as_view(), name="login"),
    path("register/", SecureRegisterView.as_view(), name="register"),
    path("me/", me, name="me"),
]
