from django.shortcuts import render
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import CustomLoginSerializer
from rest_framework import viewsets, status
from .serializers import CustomLoginSerializer
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from .models import ExecutiveMeeting
from rest_framework import serializers
from rest_framework import generics
from .serializers import ExecutiveMeetingSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .models import Purpose, Room, Vehicle, Booking, Departement, CustomUser
from .serializers import SubstituteExecutiveSerializer, ParticipantsUserSerializer, ParticipantsDepartmentSerializer
from .serializers import ExecutiveMeetingSerializer, PurposeSerializer, RoomSerializer, VehicleSerializer, BookingSerializer, DepartementSerializer
from bookingsystem.enums import UserRoles
from bookingsystem.utils.notification import (
    FCMNotification,
    FirebaseNotificationPayload,
)
from .serializers import (
    PurposeSerializer,
    RoomSerializer,
    VehicleSerializer,
    BookingSerializer,
    DepartementSerializer,
)

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        departement_name = user.departement.name if hasattr(user, 'departement') and user.departement else None

        return Response({
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "role": user.get_role_display(),
            "departement": departement_name
        })

class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CustomLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key
        })

        departement_name = user.departement.name if hasattr(user, 'departement') and user.departement else None

        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "role": user.get_role_display(),
            "departement": user.departement.name if user.departement else None
        })


class SubstituteExecutiveListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(role__in=[
        UserRoles.ADMIN.value,
        UserRoles.DEPARTMENT_CHIEF.value,
        UserRoles.DIRECTOR.value,
        UserRoles.EXECUTIVE.value,
        UserRoles.STAFF.value
    ])
    serializer_class = SubstituteExecutiveSerializer
    permission_classes = [IsAuthenticated]

class ParticipantsUserListView(generics.ListAPIView):
    queryset = CustomUser.objects.exclude(role=UserRoles.DRIVER.value)
    serializer_class = ParticipantsUserSerializer
    permission_classes = [IsAuthenticated]

class ParticipantsDepartmentListView(generics.ListAPIView):
    queryset = Departement.objects.all()
    serializer_class = ParticipantsDepartmentSerializer
    permission_classes = [IsAuthenticated]


class PurposeViewSet(ModelViewSet):
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer


class ExecutiveMeetingViewSet(viewsets.ModelViewSet):
    queryset = ExecutiveMeeting.objects.all().order_by('-start_time')
    serializer_class = ExecutiveMeetingSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        meeting = serializer.save(requester_name=self.request.user)
        invited_users = serializer.validated_data.get('invited_users', [])
        substitute_executives = serializer.validated_data.get('substitute_executive', [])

        for user in invited_users:
            user.email_user(
                subject="Invitation for Executive Meeting",
                message=f"You are invited to the meeting: {meeting.agenda}\nTime: {meeting.start_time} - {meeting.end_time}",
            )

        if substitute_executive:
            substitute_executive.email_user(
                subject="You are Appointed as the Meeting Substitute",
                message=f"You were appointed as an alternate to the Executive Director at the meeting: {meeting.agenda}\nTime: {meeting.start_time} - {meeting.end_time}",
            )


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('room', 'vehicle', 'departement').all()
    serializer_class = BookingSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        print(f"Token accepted: {request.META.get('HTTP_AUTHORIZATION')}")
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        drivers = CustomUser.objects.filter(role=UserRoles.DRIVER.value)
        payload = FirebaseNotificationPayload(
            title="Hooray! A New Booking Just Came In!",
            body="A new booking has just been secured! Don't miss the chance to prepare and make this event unforgettable. Click here for more information!",
            data={"click_action": f"/admin/bookingsystem/booking/{response.data['id']}/change/", 'ref': f"booking:{response.data['id']}"},
        )
        FCMNotification(payload).send(
            users=list(drivers)
        )

        return response

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            booking = serializer.save(requester_name=self.request.user)
        else:
            raise serializers.ValidationError({
                "requester_name": "Authentication credentials were not provided."
            })

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def available(self, request):
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        if not start_time or not end_time:
            return Response(
                {"error": "start_time and end_time are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            start_time = datetime.fromisoformat(start_time)
            end_time = datetime.fromisoformat(end_time)
        except ValueError:
            return Response(
                {"error": "start_time and end_time must be in ISO-8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if start_time >= end_time:
            return Response(
                {"error": "start_time must be earlier than end_time."},
                status=status.HTTP_400_BAD_REQUEST
            )
        available_rooms = Room.objects.exclude(
            booking__start_time__lt=end_time,
            booking__end_time__gt=start_time,
            booking__status='Approved'
        )
        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def available(self, request):
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        if not start_time or not end_time:
            return Response(
                {"error": "start_time and end_time are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            start_time = datetime.fromisoformat(start_time)
            end_time = datetime.fromisoformat(end_time)
        except ValueError:
            return Response(
                {"error": "start_time and end_time must be in ISO-8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if start_time >= end_time:
            return Response(
                {"error": "start_time must be earlier than end_time."},
                status=status.HTTP_400_BAD_REQUEST
            )
        available_vehicles = Vehicle.objects.exclude(
            booking__start_time__lt=end_time,
            booking__end_time__gt=start_time,
            booking__status='Approved'
        )
        serializer = self.get_serializer(available_vehicles, many=True)
        return Response(serializer.data)

class DepartementViewSet(viewsets.ModelViewSet):
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

def dashboard(request):
    rooms = Room.objects.all()
    vehicles = Vehicle.objects.all()
    bookings = Booking.objects.select_related('room', 'vehicle', 'departement').all()
    executive_meetings = ExecutiveMeeting.objects.all()
    departements = Departement.objects.all()
    context = {
        'rooms': rooms,
        'vehicles': vehicles,
        'bookings': bookings,
        'executive_meetings': executive_meetings,
        'departements': departements,
    }
    return render(request, 'dashboard.html', context)
