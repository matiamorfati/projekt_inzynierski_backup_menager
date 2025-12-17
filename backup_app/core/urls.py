from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    # Widoki HTML
    path('', views.dashboard, name='dashboard'),
    path('history/', views.history, name='history'),
    path('login/', views.login_view, name='login'),
    path('create-backup/', views.create_backup, name='create_backup'),
    path('settings/', views.settings_view, name='settings'),
    path('register/', views.register, name='register'),
    # API – system / backups / profiles / restore / scheduler / reports
    path('api/status/', views.api_system_status, name='api_system_status'),
    path('api/backups/run/', views.api_run_backup_from_sources, name='api_run_backup_from_sources'),
    path('api/backups/run-profile/', views.api_run_backup_from_profile, name='api_run_backup_from_profile'),
    path('api/backups/history/', views.api_backup_history, name='api_backup_history'),
    path('api/profiles/list/', views.api_list_backup_profiles, name='api_list_backup_profiles'),
    path('api/profiles/get/<int:profile_id>/', views.api_get_backup_profile, name='api_get_backup_profile'),
    path('api/profiles/create/', views.api_create_backup_profile, name='api_create_backup_profile'),
    path('api/restore/full/', views.api_restore_full, name='api_restore_full'),
    path('api/restore/partial/', views.api_restore_partial, name='api_restore_partial'),
    path('api/scheduler/start/', views.api_start_scheduler, name='api_start_scheduler'),
    path('api/scheduler/stop/', views.api_stop_scheduler, name='api_stop_scheduler'),
    path('api/reports/send/', views.api_send_daily_report_now, name='api_send_daily_report_now'),
]
