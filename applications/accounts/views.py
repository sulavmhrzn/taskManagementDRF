from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.projects.models import Project
from applications.tasks.models import Task
from common.envelope import envelope
from common.permissions import IsAdminUserOrCreateOnly

from .models import User
from .serializers import (
    CreateUserSerializer,
    DashboardSerializer,
    UpdateUserSerializer,
    UserSerializer,
)


class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUserOrCreateOnly]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UserSerializer
        elif self.request.method == "POST":
            return CreateUserSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        return super().perform_create(serializer)


class UserLogoutView(APIView):
    def post(self, request):
        if request.user.is_anonymous:
            return Response(data=envelope("ok", {"data": "logged out"}))
        try:
            request.user.auth_token.delete()
        except Exception as ex:
            # USE LOGGING
            print("EXCEPTION:", ex)
            return Response(
                data=envelope("fail", "Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data=envelope("ok", {"data": "logged out"}))


class UserLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response(envelope(status="ok", message={"token": token.key}))


class UserDashboardView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardSerializer

    def get(self, request, *args, **kwargs):
        data = {
            "user": request.user,
            "projects": Project.objects.filter(
                Q(created_by=request.user) | Q(team__in=[request.user])
            ).distinct(),
            "tasks": Task.objects.filter(
                Q(created_by=request.user) | Q(assigned_developers__in=[request.user])
            ).distinct(),
        }
        serializer = DashboardSerializer(data)
        return Response(envelope(status="ok", message={"data": serializer.data}))

    def patch(self, request, *args, **kwargs):
        obj = request.user
        email = request.data.get("email")
        serializer = UpdateUserSerializer(
            instance=obj, data={"email": email}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(envelope("ok", message={"data": "email updated successfully"}))
