# core_service
"""
Warstwa pośrednia między API a logiką backendu

Tu inicjalizujemy:
- DatabaseMenager
- BackupManager
- RestoreManager
- BackupScheduler
- Mail Notifier

Dodajemy do tego proste funkcje które łatwo będzie wywołać z API
"""

from __future__ import annotations

from datetime import datetime, time as time_class, timedelta
from typing import Any, Dict, List, Optional

from .utils.config import CONFIG
from .utils.logger import get_logger
from .db_manager import DatabaseManager
from .backup_manager import BackupManager
from .restore_manager import RestoreManager
from .scheduler import BackupScheduler
from .mail_notifier import MailNotifier

# Inicjalizacja core

_config = CONFIG.copy()
_logger = get_logger("CoreService")

_db = DatabaseManager(logger=_logger)
_mailer = MailNotifier(config=_config, logger=_logger, db=_db)
_backup_manager = BackupManager(config=_config, logger=_logger, db=_db, mailer=_mailer)
_restore_manager = RestoreManager(config=_config, logger=_logger, db=_db, mailer=_mailer)
_scheduler = BackupScheduler(config=_config, logger=_logger, db=_db, backup_manager=_backup_manager, mailer=_mailer)


# Pomocnicze konwersje do dictów


def _backup_row_to_dict(row: tuple) -> Dict[str, Any]:
    """
    Mapuje rekordy z backups:
    (name, custom_name, date, path, size, status, sources, description)
    na słownik wygodny do JSON
    """
    name, custom_name, date, path, size, status, sources, description = row
    return {
        "name": name,
        "custom_name": custom_name,
        "date": date,
        "path": path,
        "size": size,
        "status": status,
        "sources": sources,
        "description": description # Ewentualnie to usunąc
    }


def _parse_time_string(value: Optional[str]) -> time_class:
    """
    Bezpiecznie parsuje string HH:MM do obiektu time.
    W razie błędu zwraca godzinę 08:00 jako domyślną.
    """

    try:
        hours, minutes = str(value).split(":", 1)
        return time_class(int(hours), int(minutes))
    except Exception:
        return time_class(8, 0)


# Funkcje dla API


def get_system_status() -> Dict[str, Any]:
    """
    Prosty status systemu
    Można użyć do endpointu /health albo na dashboard
    """
    history = _db.get_backup_history(limit=1) or []
    last_backup = _backup_row_to_dict(history[0]) if history else None

    return {
        "ok": True,
        "last_backup": last_backup,
    }


# 1. Backupy


def run_backup_from_sources(sources: List[str], 
                            destination: Optional[str] = None, 
                            upload_to_drive: Optional[bool] = None,
                            description: Optional[str] = None,
                            custom_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Ręczne uruchomienie backupu z podanych ścieżek
    upload_to_drive:
    - True: Wysyłka na drvie
    - False: Brak wysyłki na drive
    - None: użyje ustawień z CONFIG["enable_drive_upload"]
    Nie używa input()
    """
    _logger.info(f"Manualny backup from sources: {sources}, "
                 f"to destination={destination}, upload_to_drive={upload_to_drive}"
    )

    _backup_manager.create_backup(sources=sources, 
                                  destination=destination,
                                  upload_to_drive=upload_to_drive,
                                  description=description,
                                  custom_name=custom_name,
    )

    history = _db.get_backup_history(limit=1) or []
    last = _backup_row_to_dict(history[0])  if history else None

    return {
        "ok": last is not None,
        "backup": last,
    }


def run_backup_from_profile(profile_id: Optional[int] = None, upload_to_drive: Optional[bool] = None) -> Dict[str, Any]:
    """
    Uruchomienie backupu na podstawie profilu (z bazy)
    Jeśli profile_id = None użyje profilu domyślnego
    upload_to_drive działą tak samo jak w run_backup_from_sources
    """
    _logger.info(f"Backup from profile (id={profile_id}), upload_to_drive={upload_to_drive}")
    _backup_manager.create_backup_from_profile(profile_id=profile_id,
                                               upload_to_drive=upload_to_drive,
    )

    history = _db.get_backup_history(limit=1) or []
    last = _backup_row_to_dict(history[0]) if history else None

    return {
        "ok": last is not None,
        "backup": last,
    }


def get_backup_history(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Historia backupów jako lista słowników
    """
    rows = _db.get_backup_history(limit=limit) or []
    return [_backup_row_to_dict(r) for r in rows]


def get_next_scheduled_backup(reference_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """
    Zwraca przybliżony termin kolejnego zaplanowanego backupu na podstawie
    ustawień schedulera lub domyślnego profilu. Dashboard jest "read-only",
    więc pokazujemy wyłącznie informację.
    """

    now = reference_time or datetime.now()

    profile = None
    try:
        profile = _db.get_default_backup_profile()
    except Exception:
        profile = None

    frequency = (
        (profile or {}).get("backup_frequency")
        or _scheduler.frequency
        or _config.get("backup_frequency")
        or "daily"
    )

    schedule_time = _parse_time_string(
        (profile or {}).get("daily_report_time") or _config.get("daily_report_time")
    )

    today_target = now.replace(
        hour=schedule_time.hour,
        minute=schedule_time.minute,
        second=0,
        microsecond=0,
    )

    frequency_lower = str(frequency).lower()

    if frequency_lower == "daily":
        next_run = today_target if today_target > now else today_target + timedelta(days=1)
    elif frequency_lower == "weekly":
        days_ahead = (0 - now.weekday()) % 7  # poniedziałek = 0
        candidate = today_target + timedelta(days=days_ahead)
        next_run = candidate if candidate > now else candidate + timedelta(days=7)
    elif frequency_lower == "monthly":
        next_run = today_target + timedelta(days=30)
    else:
        return None

    return {
        "frequency": frequency_lower,
        "next_run": next_run,
        "time_of_day": schedule_time,
    }


# 2. Profile backupów


def list_backup_profiles(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Zwraca listę profili backupu (id, name, custom_name, backup_frequency, is_default)
    """
    return _db.list_backup_profiles(limit=limit)


def get_backup_profile(profile_id: int) -> Optional[Dict[str, Any]]:
    """
    Zwraca dane profilu o danym id
    """
    return _db.get_backup_profile(profile_id)


def create_backup_profile(
        name: str,
        sources: List[str],
        backup_directory: Optional[str] = None,
        restore_directory: Optional[str] = None,
        backup_frequency: Optional[str] = None,
        daily_report_enable: bool = False,
        daily_report_time: Optional[str] = None,
        recipient_email: Optional[str] = None,
        is_default: bool = False,
        custom_name: Optional[str] = None,
        description: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Tworzy nowy profili backupu i zwraca go jako dict
    """
    sources_str = ";".join(sources)
    profile_id = _db.create_backup_profile(
        name=name,
        sources=sources_str,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
        backup_frequency=backup_frequency,
        daily_report_enable=daily_report_enable,
        daily_report_time=daily_report_time,
        recipient_email=recipient_email,
        is_default=is_default,
        custom_name=custom_name,
        description=description
    )

    if profile_id is None:
        return None
    
    return _db.get_backup_profile(profile_id)


# 3. Przywracanie (Restore)


def restore_full(backup_name: str, destination: Optional[str] = None) -> Dict[str, Any]:
    """
    Pełne przywrócenie backupu (ZIP -> katalog docelowy)
    """
    _logger.info(f"Restore full: {backup_name}")
    ok = _restore_manager.restore_backup(backup_name, destination=destination)

    meta = _db.get_backup_by_name(backup_name)
    return {
        "ok": ok,
        "backup": meta,
    }


def restore_partial(backup_name: str, selection: List[str], destination: Optional[str] = None) -> Dict[str, Any]:
    """
    Częściowe przywrócenie (tylko wybrane katalogi/elementy z ZIP)
    selection - lista prefixów z wnętrza ZIP-a (['Projekt2', 'Documents'])
    """
    _logger.info(f"Restore partial: {backup_name}, selection={selection}")
    ok = _restore_manager.restore_selected(
        backup_file=backup_name,
        selection=selection,
        destination=destination
    )

    meta = _db.get_backup_by_name(backup_name)
    return {
        "ok": ok,
        "backup": meta,
    }


# 4. Scheduler / raporty


def start_scheduler(profile_id: Optional[int] = None, upload_to_drive: Optional[bool] = None) -> Dict[str, Any]:
    """
    Startuje harmonogram:
    - ładuje ustawienia z profilu (albo domyslnego)
    - ustawia backupy i raporty dzienne
    - odpala scheduler w tle
    upload_to_drive działa jako override na czas działania schedulera
    """
    _logger.info(f"Starting scheduler (profile_id={profile_id}, upload_to_drive={upload_to_drive})")
    _scheduler.schedule_from_profile(profile_id=profile_id)
    _scheduler.start_scheduler(upload_to_drive=upload_to_drive)
    return {"ok": True}


def stop_scheduler() -> Dict[str, Any]:
    """
    Zatrzymuje scheduler
    """
    _logger.info("Stopping scheduler")
    _scheduler.stop_scheduler()
    return {"ok": True}


def send_daily_report_now() -> Dict[str, Any]:
    """
    Ręczne wysyłanie raportu dziennego 
    """
    _logger.info("Manual daily report trigger")
    ok = _mailer.send_daily_report()
    return {"ok": ok}
