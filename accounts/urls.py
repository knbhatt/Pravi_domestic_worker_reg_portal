from django.urls import path

from .views import LogoutView, OTPRequestView, OTPVerifyView, TokenRefreshView

urlpatterns = [
    path("request-otp/", OTPRequestView.as_view(), name="request-otp"),
    path("verify-otp/", OTPVerifyView.as_view(), name="verify-otp"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
]


