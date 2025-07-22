from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Address, EmailVerification, PasswordReset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin."""

    list_display = ('email', 'username', 'first_name', 'last_name',
                    'is_active', 'email_verified', 'date_joined')
    list_filter = ('is_active', 'email_verified',
                   'date_joined', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'first_name',
         'last_name', 'phone', 'avatar', 'date_of_birth')}),
        ('Verification', {'fields': ('email_verified', 'phone_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('date_joined', 'last_login')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Address admin."""

    list_display = ('user', 'address_type', 'first_name',
                    'last_name', 'city', 'state', 'is_default')
    list_filter = ('address_type', 'is_default', 'country', 'state')
    search_fields = ('user__email', 'first_name', 'last_name', 'city', 'state')
    ordering = ('user', '-is_default', '-created_at')

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Address Type', {'fields': ('address_type', 'is_default')}),
        ('Contact Info', {
         'fields': ('first_name', 'last_name', 'company', 'phone')}),
        ('Address', {'fields': ('address_line_1', 'address_line_2',
         'city', 'state', 'postal_code', 'country')}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Email verification admin."""

    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Token', {'fields': ('token', 'is_used')}),
        ('Timestamps', {'fields': ('created_at', 'expires_at')}),
    )

    readonly_fields = ('created_at', 'expires_at')


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    """Password reset admin."""

    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Token', {'fields': ('token', 'is_used')}),
        ('Timestamps', {'fields': ('created_at', 'expires_at')}),
    )

    readonly_fields = ('created_at', 'expires_at')
