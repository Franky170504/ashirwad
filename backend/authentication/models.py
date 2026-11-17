from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra fields for the default User model (mobile number)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    mobile = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"


class PasswordResetCode(models.Model):
    """One active reset request per user. Code and token are stored hashed."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_code")
    code_hash = models.CharField(max_length=64)
    token_hash = models.CharField(max_length=64, blank=True)  # set after the code is verified
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()