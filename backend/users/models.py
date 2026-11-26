from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin,BaseUserManager
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def generate_username(self, firstname, lastname):
        """Manish Suryavanshi -> ManishS. If taken: ManishS1, ManishS2, ..."""
        base_username = firstname.strip() + lastname.strip()[:1]
        username, counter = base_username, 1
        while self.model.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username

    def create_user(self, firstname, lastname, email, mobile_no, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        if not firstname or not lastname:
            raise ValueError("First name and last name are required")

        if not password:
            raise ValueError("Password is required")

        email = self.normalize_email(email)

        username = self.generate_username(firstname, lastname)

        user = self.model(
            firstname=firstname,
            lastname=lastname,
            username=username,
            email=email,
            mobile_no=mobile_no,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, firstname, lastname, email, mobile_no, password=None, **extra_fields):

        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")

        return self.create_user(
            firstname=firstname,
            lastname=lastname,
            email=email,
            mobile_no=mobile_no,
            password=password,
            **extra_fields
        )

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('accountant', 'Accountant'),
        ('designer', 'Designer'),
        ('programmer', 'Programmer'),
        ('operator', 'Operator'),
    ]

    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    username = models.CharField(
        max_length=150,
        unique=True,
        editable=False
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    email = models.EmailField(unique=True)
    mobile_no = models.CharField(max_length=15)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    login_time = models.DateTimeField(null=True, blank=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [
        'firstname',
        'lastname',
        'mobile_no'
    ]

    def __str__(self):
        return self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return f"{self.firstname} {self.lastname}".strip()

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otps"
    )

    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    reset_token_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True
    )