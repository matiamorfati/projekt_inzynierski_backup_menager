from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('history/', views.history, name='history'),
    path('login/', views.login_view, name='login'),
    path('create-backup/', views.create_backup, name='create_backup'),
    path('settings/', views.settings_view, name='settings'),
    path('register/', views.register, name='register'),
]
