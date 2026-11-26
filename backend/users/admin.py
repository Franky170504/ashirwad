from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm

from .models import CustomUser

# ---------- Branding (works with the custom admin template / CSS) ----------
admin.site.site_header = "Ashirwad Industries"
admin.site.site_title = "Ashirwad Admin"
admin.site.index_title = "Administration"
admin.site.site_url = "http://localhost:3000/login"   # the "View site" link


class CustomUserCreationForm(BaseUserCreationForm):
    """'Add user' form. Django's default one asks for a username, but yours is generated."""

    class Meta:
        model = CustomUser
        fields = ("firstname", "lastname", "email", "mobile_no", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = CustomUser.objects.generate_username(user.firstname, user.lastname)
        if commit:
            user.save()
            self.save_m2m()
        return user


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    add_form = CustomUserCreationForm

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
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    # UserAdmin's default searches first_name / last_name, which your model doesn't have
    search_fields = ('username', 'firstname', 'lastname', 'email', 'mobile_no')
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

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('firstname', 'lastname', 'email', 'mobile_no', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = (
        'username',
        'login_time',
        'logout_time',
    )