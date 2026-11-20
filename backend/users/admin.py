
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    model = CustomUser

    list_display = (
        'username',
        'firstname',
        'lastname',
        'email',
        'mobile_no',
        'role',
        'is_superuser',
        'login_time',
        'logout_time',
    )

    ordering = ('email',)

    fieldsets = (
        ('Personal Information', {
            'fields': (
                'firstname',
                'lastname',
                'username',
                'email',
                'mobile_no',
                'role',
                'password',
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Login Information', {
            'fields': (
                'login_time',
                'logout_time',
            )
        }),
    )

    readonly_fields = (
        'username',
        'login_time',
        'logout_time',
    )
