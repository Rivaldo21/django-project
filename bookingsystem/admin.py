from django.contrib import admin
from django.shortcuts import render
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from .models import Purpose
from .models import ExecutiveMeeting
from .models import Driver
from django import forms
from bookingsystem.models import CustomUser, UserRoles
from django.contrib.auth import get_user_model
from .models import Room, Vehicle, Booking, Driver, Departement
from django.core.exceptions import ValidationError
User = get_user_model()


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = '__all__'

    def clean_departement(self):
        departement = self.cleaned_data.get('departement')
        role = self.cleaned_data.get('role')

        if role != 'driver' and not departement:
            raise forms.ValidationError("Departement wajib diisi untuk user non-Driver!")

        return departement

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'departement']
    list_filter = ['role', 'departement']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'first_name', 'last_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'departement', 'password1', 'password2'),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Purpose)
class PurposeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'status')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'capacity', 'status', 'driver')
    list_filter = ('type', 'status')
    search_fields = ('name', 'driver__name')
    fields = ('name', 'type', 'capacity', 'status', 'driver')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "driver":
            kwargs["queryset"] = Driver.objects.select_related('user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = CustomUser.objects.filter(role="driver")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.license_number}"

    class Meta:
        verbose_name = "Department Chief"
        verbose_name_plural = "Department Chiefs"


class BookingAdmin(admin.ModelAdmin):
    list_display = ['resource_type', 'purpose', 'departement', 'requester_name', 'start_time', 'end_time', 'status']
    list_filter = ['status', 'resource_type', 'purpose']
    search_fields = ['requester_name__username', 'purpose__name']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "requester_name":
            kwargs["queryset"] = CustomUser.objects.exclude(role="driver")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        def get_fields(self, request, obj=None):
            fields = super().get_fields(request, obj)

            if 'description' not in fields:
                fields.append('description')

            return fields

            if 'description' not in fields:
              fields.append('description')

        return fields

    def save_model(self, request, obj, form, change):
        try:
            obj.clean()
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            form.add_error(None, e)

    def clean(self):
        cleaned_data = super().clean()
        resource_type = cleaned_data.get("resource_type")
        room = cleaned_data.get("room")
        vehicle = cleaned_data.get("vehicle")

        if resource_type == "Room" and not room:
            raise ValidationError({"room": "This field is required."})
        if resource_type == "Vehicle" and not vehicle:
            raise ValidationError({"vehicle": "This field is required."})

        return cleaned_data

admin.site.register(Booking, BookingAdmin)


@admin.register(ExecutiveMeeting)
class ExecutiveMeetingAdmin(admin.ModelAdmin):
    list_display = ['description', 'purpose', 'requester_name', 'room', 'vehicle', 'start_time', 'end_time', 'status', 'obs']
    list_filter = ['status']
    search_fields = ['description', 'purpose__name', 'requester_name__username']

    filter_horizontal = ('participants_departments', 'participants_users', 'substitute_executive')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "requester_name":
            kwargs["queryset"] = CustomUser.objects.exclude(role=UserRoles.DRIVER.value)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        🔥 Memfilter daftar user di Django Admin
        - `participants_users` → hanya Staff
        - `substitute_executive` → hanya Director & Department Chief
        """
        if db_field.name == "participants_users":
            kwargs["queryset"] = CustomUser.objects.filter(role=UserRoles.STAFF.value)  # 🔥 Hanya role Staff
        elif db_field.name == "substitute_executive":
            kwargs["queryset"] = CustomUser.objects.filter(role__in=[
                UserRoles.DIRECTOR.value, UserRoles.DEPARTMENT_CHIEF.value  # 🔥 Hanya Director & Department Chief
            ])
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    fieldsets = (
        (None, {
            'fields': (
                'description', 'purpose', 'requester_name', 'location',
                'room', 'vehicle', 'start_time', 'end_time', 'status', 'obs',
                'participants_departments', 'participants_users', 'substitute_executive'
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.save()
            form.save_m2m()

        errors = {}

        participants_departments = form.cleaned_data.get("participants_departments", [])
        participants_users = form.cleaned_data.get("participants_users", [])

        if not obj.purpose:
            errors['purpose'] = 'Purpose must be selected!'
        if not obj.obs.strip():
            errors['obs'] = 'Observation/Notes cannot be empty!'

        if errors:
            raise ValidationError(errors)

        obj.clean()
        super().save_model(request, obj, form, change)

