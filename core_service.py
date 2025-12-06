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

from typing import Any, Dict, List, Optional

from utils.config import CONFIG
from utils.logger import get_logger
from db_manager import DatabaseManager
from backup_manager import BackupManager
from restore_manager import RestoreManager
from scheduler import BackupScheduler
from mail_notifier import MailNotifier

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
    (name, date, path, size, status, sources)
    na słownik wygodny do JSON
    """
    name, date, path, size, status, sources = row
    return {
        "name": name,
        "date": date,
        "path": path,
        "size": size,
        "status": status,
        "sources": sources,
    }


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


def run_backup_from_sources(sources: List[str], destination: Optional[str] = None) -> Dict[str, Any]:
    """
    Ręczne uruchomienie backupu z podanych ścieżek
    Nie używa input()
    """
    _logger.info(f"Manualny backup from sources: {sources}")
    _backup_manager.create_backup(sources=sources, destination=destination)

    history = _db.get_backup_history(limit=1) or []
    last = _backup_row_to_dict(history[0])  if history else None

    return {
        "ok": last is not None,
        "backup": last,
    }


def run_backup_from_profile(profile_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Uruchomienie backupu na podstawie profilu (z bazy)
    Jeśli profile_id = None użyje profilu domyślnego
    """
    _logger.info(f"Backup from profile (id={profile_id})")
    _backup_manager.create_backup_from_profile(profile_id)

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


# 2. Profile backupów


def list_backup_profiles(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Zwraca listę profili backupu (id, name, backup_frequency, is_default)
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
) -> Optional[Dict[str, Any]]:
    """
    Tworzy nowy profili backupu i zwraca go jako dict
    """
    sources_str = ";".join(sources)
    profile_id = _db.create_backup_profile(
        name=name,
        sources=sources,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
        backup_frequency=backup_frequency,
        daily_report_enable=daily_report_enable,
        daily_report_time=daily_report_time,
        recipient_email=recipient_email,
        is_default=is_default,
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


def start_scheduler(profile_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Startuje harmonogram:
    - ładuje ustawienia z profilu (albo domyslnego)
    - ustawia backupy i raporty dzienne
    - odpala scheduler w tle    
    """
    _logger.info(f"Starting scheduler (profile_id={profile_id})")
    _scheduler.schedule_from_profile(profile_id=profile_id)
    _scheduler.start_scheduler()
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

