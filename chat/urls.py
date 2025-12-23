from django.urls import path

from .views import UserList, MessageList

urlpatterns = [
    path('people/', UserList.as_view(), name='people'),
    path('messages/<int:id>', MessageList.as_view(), name='messages'),
]