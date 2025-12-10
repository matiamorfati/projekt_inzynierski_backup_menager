from django.shortcuts import render

from django.shortcuts import render

def dashboard(request):
    return render(request, 'dashboard.html')

def history(request):
    return render(request, 'backup_history.html')

def login_view(request):
    return render(request, 'login.html')

def create_backup(request):
    return render(request, 'create_backup.html')

def settings_view(request):
    return render(request, 'settings.html')

def register(request):
    return render(request, 'register.html')
