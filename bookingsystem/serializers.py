from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Purpose
from .models import Booking
from django.db.models import Q
from datetime import datetime
from .models import CustomUser
from .models import ExecutiveMeeting, Departement 
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from .models import ExecutiveMeeting, Purpose, Booking, CustomUser, Room, Vehicle, Departement
from django.contrib.auth import get_user_model
from .models import UserRoles
User = get_user_model()

class CustomLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username_or_email = data.get('username_or_email')
        password = data.get('password')

        user = (
            CustomUser.objects.filter(username=username_or_email).first() or
            CustomUser.objects.filter(email=username_or_email).first()
        )

        if not user or not user.check_password(password):
            raise AuthenticationFailed("Invalid username/email or password.")

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        return {"user": user}

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class RoomSerializer(serializers.ModelSerializer):
    in_use = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = '__all__'

    def get_in_use(self, obj):
        request = self.context.get('request')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        try:
            if start_time and end_time:
                start_time = datetime.fromisoformat(start_time)
                end_time = datetime.fromisoformat(end_time)
                return obj.is_in_use(start_time, end_time)
        except (ValueError, TypeError):
            return False
        return False


class VehicleSerializer(serializers.ModelSerializer):
    in_use = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = '__all__'

    def get_in_use(self, obj):
        request = self.context.get('request')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        try:
            if start_time and end_time:
                start_time = datetime.fromisoformat(start_time)
                end_time = datetime.fromisoformat(end_time)
                return obj.is_in_use(start_time, end_time)
        except (ValueError, TypeError):
            return False
        return False

    def get_driver_name(self, obj):
        return obj.driver.user.get_full_name() if obj.driver and obj.driver.user else "No Driver Assigned"


class SubstituteExecutiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ParticipantsUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ParticipantsDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departement
        fields = ['id', 'name']


class DepartementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departement
        fields = '__all__'

class PurposeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purpose
        fields = '__all__'


class ExecutiveMeetingSerializer(serializers.ModelSerializer):
    requester_name = UserSerializer(read_only=True)  # Mengubah ID jadi Nama
    substitute_executive = UserSerializer(read_only=True)  # Menampilkan Nama Pengganti
    participants = DepartementSerializer(many=True, read_only=True)
    
    # Gunakan PrimaryKeyRelatedField untuk Room & Vehicle
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False, allow_null=True)
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), required=False, allow_null=True)

    # Field baru untuk format tanggal
    formatted_start_time = serializers.SerializerMethodField()
    formatted_end_time = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveMeeting
        fields = [
            'id', 'description', 'requester_name', 'location', 'participants',
            'room', 'vehicle', 'substitute_executive',
            'start_time', 'end_time', 'formatted_start_time', 'formatted_end_time',
            'status', 'obs'
        ]

    def get_formatted_start_time(self, obj):
        return obj.start_time.strftime('%d-%m-%Y %H:%M') if obj.start_time else None

    def get_formatted_end_time(self, obj):
        return obj.end_time.strftime('%d-%m-%Y %H:%M') if obj.end_time else None

    def validate(self, data):
        """
        Validasi agar Participants dan Obs wajib diisi.
        """
        if not self.instance and not data.get('participants'):
            raise serializers.ValidationError({"participants": "Participants harus dipilih minimal 1!"})

        if not data.get('obs'):
            raise serializers.ValidationError({"obs": "Observation/Notes tidak boleh kosong!"})

        return data


class BookingSerializer(serializers.ModelSerializer):
    room_details = RoomSerializer(source='room', read_only=True)
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    purpose_details = PurposeSerializer(source='purpose', read_only=True)
    departement_details = DepartementSerializer(source='departement', read_only=True)
    formatted_start_time = serializers.SerializerMethodField()
    formatted_end_time = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'resource_type', 'purpose', 'purpose_details',
            'room', 'room_details',
            'vehicle', 'vehicle_details',
            'departement', 'departement_details',
            'requester_name', 'start_time', 'end_time',
            'formatted_start_time', 'formatted_end_time',
            'destination_address', 'description', 'status',
        ]
        read_only_fields = ['status', 'requester_name']

    def validate(self, data):
        # Validasaun oras
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if not start_time or not end_time:
            raise serializers.ValidationError("Both start_time and end_time must be provided.")
        if start_time >= end_time:
            raise serializers.ValidationError("start_time must be earlier than end_time.")

        if 'purpose' not in data or not data.get('purpose'):
            raise serializers.ValidationError("Purpose is required.")

        resource_type = data.get('resource_type')
        if resource_type == 'Room':
            if not data.get('room'):
                raise serializers.ValidationError("Room must be selected for Room bookings.")
            if data.get('vehicle'):
                raise serializers.ValidationError("Vehicle cannot be selected for Room bookings.")
        elif resource_type == 'Vehicle':
            if not data.get('vehicle'):
                raise serializers.ValidationError("Vehicle must be selected for Vehicle bookings.")
            if not data.get('destination_address'):
                raise serializers.ValidationError("Destination address is required for Vehicle bookings.")
        else:
            raise serializers.ValidationError("Invalid resource_type. Must be 'Room' or 'Vehicle'.")

        # Validasaun konflitu booking
        overlapping_bookings = Booking.objects.filter(
            resource_type=resource_type,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(status__in=['Rejected', 'Cancelled'])

        if resource_type == 'Room':
            overlapping_bookings = overlapping_bookings.filter(room=data.get('room'))
        elif resource_type == 'Vehicle':
            overlapping_bookings = overlapping_bookings.filter(vehicle=data.get('vehicle'))

        if overlapping_bookings.exists():
            raise serializers.ValidationError(
                f"The selected {resource_type} is already booked for the given time range."
            )

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['requester_name'] = request.user
        else:
            raise serializers.ValidationError({
                "requester_name": "Authentication credentials were not provided."
            })

        validated_data['status'] = 'Pending'
        return super().create(validated_data)

    def get_formatted_start_time(self, obj):
        return obj.start_time.strftime('%d-%m-%Y %H:%M') if obj.start_time else None

    def get_formatted_end_time(self, obj):
        return obj.end_time.strftime('%d-%m-%Y %H:%M') if obj.end_time else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.resource_type == 'Room':
            representation.pop('vehicle_details', None)
        elif instance.resource_type == 'Vehicle':
            representation.pop('room_details', None)
        return representation


