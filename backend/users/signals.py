
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def update_login_time(sender, request, user, **kwargs):
    user.login_time = timezone.now()
    user.save(update_fields=['login_time'])


@receiver(user_logged_out)
def update_logout_time(sender, request, user, **kwargs):
    if user:
        user.logout_time = timezone.now()
        user.save(update_fields=['logout_time'])
