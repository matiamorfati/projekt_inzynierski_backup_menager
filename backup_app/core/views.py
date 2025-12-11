from django.shortcuts import render

from django.shortcuts import render

from django.http import JsonResponse, HttpResponseBadRequest

from django.views.decorators.csrf import csrf_exempt

import json

from . import core_service

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

# ------------------------------
# API views — wrappers dla core_service
# ------------------------------
def api_system_status(request):
    return JsonResponse(core_service.get_system_status())


@csrf_exempt
def api_run_backup_from_sources(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    data = json.loads(request.body or "{}")
    sources = data.get("sources", [])
    destination = data.get("destination")
    result = core_service.run_backup_from_sources(sources=sources, destination=destination)
    return JsonResponse(result)


@csrf_exempt
def api_run_backup_from_profile(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    data = json.loads(request.body or "{}")
    profile_id = data.get("profile_id")
    result = core_service.run_backup_from_profile(profile_id=profile_id)
    return JsonResponse(result)


def api_backup_history(request):
    try:
        limit = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    history = core_service.get_backup_history(limit=limit)
    return JsonResponse({"backups": history})


def api_list_backup_profiles(request):
    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    profiles = core_service.list_backup_profiles(limit=limit)
    return JsonResponse({"profiles": profiles})


def api_get_backup_profile(request, profile_id):
    profile = core_service.get_backup_profile(profile_id)
    return JsonResponse({"profile": profile})


@csrf_exempt
def api_create_backup_profile(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    data = json.loads(request.body or "{}")
    profile = core_service.create_backup_profile(
        name=data.get("name"),
        sources=data.get("sources", []),
        backup_directory=data.get("backup_directory"),
        restore_directory=data.get("restore_directory"),
        backup_frequency=data.get("backup_frequency"),
        daily_report_enable=data.get("daily_report_enable", False),
        daily_report_time=data.get("daily_report_time"),
        recipient_email=data.get("recipient_email"),
        is_default=data.get("is_default", False),
    )
    return JsonResponse({"profile": profile})


@csrf_exempt
def api_restore_full(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    data = json.loads(request.body or "{}")
    backup_name = data.get("backup_name")
    destination = data.get("destination")
    result = core_service.restore_full(backup_name=backup_name, destination=destination)
    return JsonResponse(result)


@csrf_exempt
def api_restore_partial(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    data = json.loads(request.body or "{}")
    backup_name = data.get("backup_name")
    selection = data.get("selection", [])
    destination = data.get("destination")
    result = core_service.restore_partial(backup_name=backup_name, selection=selection, destination=destination)
    return JsonResponse(result)


@csrf_exempt
def api_start_scheduler(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    data = json.loads(request.body or "{}")
    profile_id = data.get("profile_id")
    result = core_service.start_scheduler(profile_id=profile_id)
    return JsonResponse(result)


def api_stop_scheduler(request):
    result = core_service.stop_scheduler()
    return JsonResponse(result)


def api_send_daily_report_now(request):
    result = core_service.send_daily_report_now()
    return JsonResponse(result)