from django.urls import re_path
from . import views

# "/?" makes the trailing slash optional, so both /login and /login/ work
urlpatterns = [
    re_path(r"^csrf/?$", views.csrf),
    # re_path(r"^register/?$", views.register),
    re_path(r"^login/?$", views.login),
    re_path(r"^forgot-password/?$", views.forgot_password),
    re_path(r"^verify-code/?$", views.verify_otp),
    re_path(r"^set-password/?$", views.set_new_password),
    re_path(r"^me/?$", views.me),
    re_path(r"^logout/?$", views.logout_view),
]