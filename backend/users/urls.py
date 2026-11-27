from django.urls import re_path
from . import views

# "/?" makes the trailing slash optional, so both /login and /login/ work
urlpatterns = [
    re_path(r"^csrf/?$", views.csrf),
    re_path(r"^login/?$", views.login),
    re_path(r"^forgot-password/?$", views.forgot_password),
    re_path(r"^verify-code/?$", views.verify_otp),
    re_path(r"^set-password/?$", views.set_new_password),
    re_path(r"^me/?$", views.me),
    re_path(r"^logout/?$", views.logout_view),
    re_path(r"^change-password/?$", views.change_password),
    re_path(r"^verify-login-otp/?$", views.verify_login_otp),
    re_path(r"^resend-login-otp/?$", views.resend_login_otp),
]