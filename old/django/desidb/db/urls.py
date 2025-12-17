from django.urls import path
from django.conf.urls import include
from db import views

urlpatterns = [
    path('runsqlquery', views.RunSQLQuery.as_view()),
]
