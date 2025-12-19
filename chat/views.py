from django.contrib.auth.models import User
from rest_framework import mixins, generics, permissions

from authentication.authentication import CookieJWTAuthentication
from .serializers import UserSerializer


# Create your views here.
class UserList(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request):
        return self.list(request)