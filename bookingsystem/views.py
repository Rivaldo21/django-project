from django.shortcuts import render
from rest_framework import viewsets
from .models import Room, Vehicle, Booking
from .serializers import RoomSerializer, VehicleSerializer, BookingSerializer

# ViewSet untuk Room
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

# ViewSet untuk Vehicle
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

# ViewSet untuk Booking
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

# Fungsi dashboard
def dashboard(request):
    rooms = Room.objects.all()
    vehicles = Vehicle.objects.all()
    bookings = Booking.objects.all()
    context = {
        'rooms': rooms,
        'vehicles': vehicles,
        'bookings': bookings,
    }
    return render(request, 'dashboard.html', context)