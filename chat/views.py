from django.contrib.auth.models import User
from rest_framework import mixins, generics, permissions

from authentication.authentication import CookieJWTAuthentication

from .models import Message
from .serializers import UserSerializer, MessageSerializer


# Create your views here.
class UserList(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request):
        return self.list(request)

class MessageList(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        username = self.kwargs['username']
        user = User.objects.get(username=username)

        # Example: messages where user is sender OR receiver
        return Message.objects.filter(
            sender=user
        ) | Message.objects.filter(
            recipient=user
        )

    def get(self, request, username):
        return self.list(request)