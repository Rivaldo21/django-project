from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from bookingsystem.enums import UserRoles
from django.conf import settings
User = settings.AUTH_USER_MODEL

class Departement(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True 

class CustomUser(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[MinLengthValidator(1)],
        error_messages={
            'unique': "A user with that username already exists.",
        },
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    ROLE_CHOICES = [
        (UserRoles.ADMIN.value, "Admin"),
        (UserRoles.DEPARTMENT_CHIEF.value, "Department Chief"),
        (UserRoles.DIRECTOR.value, "Director"),  
        (UserRoles.EXECUTIVE.value, "Executive"),
        (UserRoles.STAFF.value, "Staff"),  
        (UserRoles.DRIVER.value, "Driver"),
    ]

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=UserRoles.ADMIN.value,  
        blank=False,
        null=False
    )

    departement = models.ForeignKey(
        Departement,  
        on_delete=models.CASCADE,
        related_name="users",
        null=False,
        blank=True,
        verbose_name="Department"
    )

    def clean(self):
        if self.role != UserRoles.DRIVER.value and not self.departement:
            raise ValidationError({"departement": "Department required for non-Driver users!"})

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        departement_name = self.departement.name if self.departement else "No Department"
        return f"{self.username} - {self.get_role_display()} - {departement_name}"

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'role', 'departement']

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.username} - {self.get_role_display()} - {self.departement.name}"

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True,
    )

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"


class Departement(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Driver(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'driver'},
        verbose_name="Driver"
    )
    license_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        full_name = self.user.get_full_name().strip() if self.user else "No Name"
        return f"{full_name} - {self.license_number}"


class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    status = models.CharField(max_length=50, choices=[
        ('Available', 'Available'),
        ('In Use', 'In Use'),
        ('Under Maintenance', 'Under Maintenance'),
    ])

    def __str__(self):
        return self.name

    def is_in_use(self, start_time, end_time):
        return self.bookings.filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='Approved'
        ).exists()


class Vehicle(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=[
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Van', 'Van'),
        ('Truck', 'Truck'),
    ])
    capacity = models.IntegerField()
    status = models.CharField(max_length=50, choices=[
        ('Available', 'Available'),
        ('In Use', 'In Use'),
        ('Under Maintenance', 'Under Maintenance'),
    ])
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles'
    )

    def __str__(self):
        if self.driver and self.driver.user:
            driver_name = self.driver.user.get_full_name()
            return f"{self.name} ({driver_name} - {self.driver.license_number})"
        return f"{self.name} (No Driver)"


    def is_in_use(self, start_time, end_time):
        return self.bookings.filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='Approved'
        ).exists()

class Purpose(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('Room', 'Room'),
        ('Vehicle', 'Vehicle'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    resource_type = models.CharField(max_length=50, choices=RESOURCE_TYPE_CHOICES)
    purpose = models.ForeignKey(Purpose, on_delete=models.SET_NULL, null=True, blank=False, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    destination_address = models.TextField(null=True, blank=True)
    requester_name = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Requester'
    )
    departement = models.ForeignKey(Departement,on_delete=models.CASCADE,  null=False,  blank=False, related_name='bookings')  
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(null=False, blank=False)
    destination_address = models.CharField(max_length=255, null=True, blank=True)   
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def clean(self):
        super().clean()
        if self.resource_type == "Vehicle" and not self.destination_address:
            raise ValidationError({"destination_address": "This field is required."})        

    def clean(self):
        super().clean()
        if self.resource_type == "Room" and not self.room:
            raise ValidationError({"room": "This field is required."})
        if self.resource_type == "Vehicle" and not self.vehicle:
            raise ValidationError({"vehicle": "This field is required."})
        if not self.description:
            raise ValidationError({"description": "This field is required."})

class FCMToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=False, related_name='fcm_tokens')
    token = models.CharField(max_length=255)

    def __str__(self):
        return self.token

class UserNotification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    payload = models.JSONField()
    is_read = models.BooleanField(default=False)
    fcm_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"
    
class ExecutiveMeeting(models.Model):
    description = models.CharField(max_length=255)
    requester_name = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_meetings',
        verbose_name='Requester'
    )
    location = models.CharField(max_length=255)
    purpose = models.ForeignKey(
        Purpose,
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="executive_meetings"
    )
     
    participants_departments = models.ManyToManyField(
        Departement,
        related_name="meeting_participants",
        blank=True  
    )
    participants_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="meeting_participant_users",
        blank=True,
        limit_choices_to={'role__in': [
            UserRoles.ADMIN.value,
            UserRoles.DEPARTMENT_CHIEF.value,
            UserRoles.DIRECTOR.value,
            UserRoles.EXECUTIVE.value,
            UserRoles.STAFF.value
        ]}
    )

    substitute_executive = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    related_name="substituted_meetings",
    blank=True,
    limit_choices_to={'role__in': [
        UserRoles.ADMIN.value,
        UserRoles.DEPARTMENT_CHIEF.value,
        UserRoles.DIRECTOR.value,
        UserRoles.EXECUTIVE.value,
        UserRoles.STAFF.value
      ]}
    )
    room = models.ForeignKey(
        'Room',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="executive_meetings"
    )
    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="executive_meetings"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50, choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Execute", "Execute"), ("Cancelled", "Cancelled"),])
    obs = models.TextField(null=False, blank=False)

    def __str__(self):
        return self.description

    def clean(self):
        super().clean()

        if not self.pk: 
            return   

        def clean(self):
            super().clean()
            if not self.participants_departments.exists() and not self.participants_users.exists():
                raise ValidationError({"participants_users": "Participants must be selected at least 1 (Department or User)!"})
    
