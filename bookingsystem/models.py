from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from bookingsystem.enums import UserRoles

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
    role = models.CharField(
        max_length=50,
        choices=UserRoles.choices(),
        default=UserRoles.ADMIN.value,
        blank=False,
        null=True
    )

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

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'role']

    def __str__(self):
        return self.username

class Departement(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Driver(models.Model):
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


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
        return f"{self.name} ({self.driver.name if self.driver else 'No Driver'})"

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
         ('Executive Meeting', 'Executive Meeting'),
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
    departement = models.ForeignKey(
        Departement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )

    destination_address = models.CharField(max_length=255, null=True, blank=True)
    travel_description = models.TextField(null=False, blank=False)
    requester_name = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Requester'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.resource_type} Booking for {self.purpose} by {self.requester_name}"

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
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    agenda = models.CharField(max_length=255)
    purpose = models.ForeignKey('Purpose', on_delete=models.SET_NULL, null=True, related_name='executive_meetings')
    requester_name = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='executive_meetings')
    location = models.CharField(max_length=255)
    participants = models.TextField(help_text="List of participants (separated by commas)")
    departement = models.ForeignKey('Departement', on_delete=models.SET_NULL, null=True, related_name='executive_meetings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Executive Meeting: {self.agenda} by {self.requester_name}"