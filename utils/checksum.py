#checksum
#sprawdzanie integralności plików backupa
"""
checksum.py - funkcje do obliczania i weryfikacji sum kontrolnych.
Domyślnie używa SHA-256. Zawiera:
- calculate_checksum(file_path, algo="sha256", chunk_size=1MB)
- verify_checksum(file_path, expected_hash, algo="sha256")
- opcjonalne: manifest katalogu (hashy plików) do późniejszej weryfikacji.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Optional
import logging
from utils.logger import get_logger

module_logger = get_logger("Checksum")

# Podstawowe API plikowe

def calculate_checksum(
        file_path: str,
        algo: str = "sha256",
        chunk_size: int = 1024 * 1024,
        logger: logging.Logger = None,
) -> str:
    """
    Oblicza sumę kontrolną pliku w trybie streamingowym (nie wczytuje całego do RAM).
    :param file_path: ścieżka do pliku
    :param algo: nazwa algorytmu (np. 'sha256', 'md5', 'sha1' - rekomendowane sha256)
    :param chunk_size: rozmiar kawałka czytania (domyślnie 1 MB)
    :param logger: obcjonalny logger (musi mieć .debug/.error)
    :return: heksadecymalny hash (np. 'a3b2...')

    Raises:
        FileNotFoundError - gdy plik nie istnieje
        ValueError - gdy algorytm nie jest obsługiwany.
    """
    logger = logger or module_logger

    if not os.path.exists(file_path):
        msg = f"Plik nie istnieje: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    try:
        h = hashlib.new(algo)
    except Exception as e:
        msg = f"Nieobsługiwany algorytm: {algo} ({e})"
        logger.error(msg)
        raise ValueError(msg)
    
    logger.debug(f"Liczenie {algo} dla: {file_path}")

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    
    digest = h.hexdigest()
    logger.debug(f"{algo}({file_path}) = {digest}")
    return digest

def verify_checksum(
        file_path: str,
        expected_hash: str,
        algo: str = "sha256",
        chunk_size: int = 1024 * 1024,
        logger: logging.Logger = None,
) -> bool:
    """
    Porównuje obliczony hash z oczekownym.
    :return: True jeśli zgodne, False w przeciwnym razie.
    """
    logger = logger or module_logger
    try:
        actual = calculate_checksum(file_path, algo=algo, chunk_size=chunk_size, logger=logger)
    except Exception:
        return False
    ok = (actual.lower() == (expected_hash or "").lower()) 
    if ok:
        logger.debug(f"Checkum OK dla: {file_path}")   
    else:
        logger.error(f"Checksum NIEZGODNY dla: {file_path} (actual={actual}, expected={expected_hash})")
    return ok


def build_dir_manifest(
        dir_path: str,
        algo: str = "sha256",
        logger: logging.Logger = None,
) -> Dict[str, Dict[str, int | str]]:
    """
    Tworzy manifest {relative_path: {"hash": <sha>, "size": <bytes>}, ...}
    :param dir_path: katalog źródłowy
    """
    logger = logger or module_logger

    if not os.path.isdir(dir_path):
        msg = f"To nie jest katalog: {dir_path}"
        logger.error(msg)
        raise NotADirectoryError(msg)
    
    manifest: Dict[str, Dict[str, int | str]] = {}
    base = os.path.abspath(dir_path)

    for root, _, files in os.walk(base):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, base)
            try:
                h = calculate_checksum(full, algo=algo, logger=logger)
                size = os.path.getsize(full)
                manifest[rel] = {"hash": h, "size": size}
            except Exception as e:
                logger.error(f"Pominięto '{full}' ({e})")

    logger.debug(f"Zbudowano manifest dla: {dir_path} (plików: {len(manifest)})")
    return manifest


def save_manifest(manifest: Dict[str, Dict[str, int | str]], path: str) -> None:
    """
    Zapisuje manifest do JSON (UTF-8, pretty).
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def load_manifest(path: str) -> Dict[str, Dict[str, int | str]]:
    """
    Wczytanie manifestu
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    

def verify_manifest(
    dir_path: str,
    manifest: Dict[str, Dict[str, int | str]],
    algo: str = "sha256",
    logger: logging.Logger = None,
) -> bool:
    """
    Sprawdza, czy wszystkie pliki z manifesty istnieją i mają zgodne hashe.
    :return: True gdy wszystko sie zgadza
    """
    logger = logger or module_logger
    base = os.path.abspath(dir_path)
    all_ok = True

    for rel, meta in manifest.items():
        full = os.path.join(base, rel)
        expected = str(meta.get("hash", ""))
        if not os.path.exists(full):
            logger.error(f"Brak pliku: {full}")
            all_ok = False
            continue
        if not verify_checksum(full, expected, algo=algo, logger=logger):
            all_ok = False
        
    return all_ok



# Test Manualny

if __name__ == "__main__":
    # Prosty self-test: policz hash tego pliku i zweryfikuj
    test_file = __file__
    digest = calculate_checksum(test_file)
    print("SHA256:", digest)
    print("Verify:", verify_checksum(test_file, digest))
