from django.urls import path

from .views import UserList

urlpatterns = [
    path('people/', UserList.as_view(), name='people'),
]