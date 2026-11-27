from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser

# ---------- Branding ----------
admin.site.site_header = "Ashirwad Industries"
admin.site.site_title = "Ashirwad Admin"
admin.site.index_title = "Administration"
admin.site.site_url = "http://localhost:3000/login"   # the "View site" link


class CustomUserCreationForm(forms.ModelForm):
    """'Add user' form. Username is generated and the default password equals the username."""

    class Meta:
        model = CustomUser
        fields = ("firstname", "lastname", "email", "mobile_no", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = CustomUser.objects.generate_username(user.firstname, user.lastname)
        user.set_password(user.username)   # default password = username
        if commit:
            user.save()
            self.save_m2m()
        return user

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    add_form = CustomUserCreationForm

    list_display = (
        'username', 'firstname', 'lastname', 'email', 'mobile_no',
        'role', 'is_superuser', 'login_time', 'logout_time',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'firstname', 'lastname', 'email', 'mobile_no')
    ordering = ('email',)
    actions = ['reset_password_to_username']

    fieldsets = (
        ('Personal Information', {
            'fields': ('firstname', 'lastname', 'username', 'email', 'mobile_no', 'role', 'password'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Login Information', {
            'fields': ('login_time', 'logout_time'),
        }),
    )

    # No password1/password2 any more
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('firstname', 'lastname', 'email', 'mobile_no', 'role'),
        }),
    )
    readonly_fields = ('username', 'login_time', 'logout_time')

    @admin.action(description="Reset password to username")
    def reset_password_to_username(self, request, queryset):
        for user in queryset:
            user.set_password(user.username)
            user.save(update_fields=["password"])
        self.message_user(
            request,
            f"Password reset to username for {queryset.count()} user(s).",
            messages.SUCCESS,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            self.message_user(
                request,
                f"User created. Username and default password: {obj.username}",
                messages.INFO,
            )