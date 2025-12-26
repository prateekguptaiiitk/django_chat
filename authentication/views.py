from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .authentication import CookieJWTAuthentication
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer
from .utils import set_auth_cookies, get_tokens_for_user


# Create your views here.
class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        tokens = get_tokens_for_user(user)

        response = Response(
            {"message": "User registered successfully", "id": user.id},
            status=status.HTTP_201_CREATED
        )

        set_auth_cookies(
            response,
            access=str(tokens['access']),
            refresh=str(tokens['refresh'])
        )
        return response

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)

            response = Response({"message": "Login successful", "id": user.id})
            set_auth_cookies(
                response,
                access=str(tokens['access']),
                refresh=str(tokens['refresh'])
            )
            return response

class LogoutAPIView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        response = Response({"message": "Logged out"})

        response.set_cookie(
            key="access",
            value="",
            expires=timezone.now() - timedelta(days=1),
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )

        response.set_cookie(
            key="refresh",
            value="",
            expires=timezone.now() - timedelta(days=1),
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )

        return response

class ProfileAPIView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(instance=request.user)

        return Response({
            "user": serializer.data,
        })

class CookieTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get("refresh")

        if not refresh:
            return Response({"detail": "No refresh token"}, status=401)

        serializer = self.get_serializer(data={"refresh": refresh})
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data["access"]

        response = Response({"access": "refreshed"})
        response.set_cookie(
            "access",
            access,
            httponly=True,
            secure=True,
            samesite="None",
            path="/",
        )
        return response