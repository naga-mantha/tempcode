from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib import admin

admin.site.register(Permission)

class UserAdmin(UserAdmin):
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'employee_code')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
                )
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
        # ('Orders Planning/PM', {
        #     'fields': ("wo_columns", "po_line_columns",
        #                "so_line_columns", "top_report_columns", "inventory_columns")
        # }),
    )
admin.site.register(CustomUser, UserAdmin)