from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
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
        user = get_object_or_404(User, username=username)
        our_user = self.request.user

        if user == our_user:
            return Message.objects.none()

        print('user', user, 'our_user', our_user)
        return Message.objects.filter(
            Q(sender=user, recipient=our_user) |
            Q(sender=our_user, recipient=user)
        ).order_by("created_at")

    def get(self, request, *args, **kwargs):
        return self.list(request,  *args, **kwargs)