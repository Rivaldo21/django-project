from django.urls import path, include
from .views import LoginAPIView
from rest_framework.routers import DefaultRouter
from .views import ExecutiveMeetingViewSet
from .views import RoomViewSet, VehicleViewSet, BookingViewSet, DepartementViewSet
from rest_framework.authtoken.views import obtain_auth_token
from .views import LoginAPIView, UserProfileAPIView
from .views import (
    LoginAPIView, ExecutiveMeetingViewSet, RoomViewSet, VehicleViewSet, 
    BookingViewSet, DepartementViewSet, SubstituteExecutiveListView, 
    ParticipantsUserListView, ParticipantsDepartmentListView
)

router = DefaultRouter()
router.register('rooms', RoomViewSet)
router.register('vehicles', VehicleViewSet)
router.register('bookings', BookingViewSet)
router.register('departements', DepartementViewSet)
router.register('executive-meetings', ExecutiveMeetingViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', obtain_auth_token, name='api_login'),
    path('api/user/', UserProfileAPIView.as_view(), name='api_user'),
    path('api/substitute-executives/', SubstituteExecutiveListView.as_view(), name='substitute-executives'),
    path('api/participants-users/', ParticipantsUserListView.as_view(), name='participants-users'),
    path('api/participants-departments/', ParticipantsDepartmentListView.as_view(), name='participants-departments'),
]