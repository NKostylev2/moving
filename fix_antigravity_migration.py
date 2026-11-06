#!/usr/bin/env python3
"""
fix_antigravity_migration.py
Починка и перенос проектов Antigravity (включая AI-Dubbing и все чаты) с Windows на Linux.

Что делает:
1. Копирует conversation_summaries.db с Windows
2. Заменяет Windows-пути (file:///e%3A/AI-Dubbing) на Linux-пути (file:///mnt/ai/AI-Dubbing)
3. Копирует все базы чатов (conversations/*.db)
4. Копирует все папки чатов (brain/*)
5. Переносит app_storage.json в ~/.config/Antigravity/ (для отображения проектов в боковом меню)
6. Копирует knowledge, config (скиллы), antigravity_state.pbtxt
"""

import os
import sys
import shutil
import sqlite3
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Fix Antigravity Windows to Linux migration")
    parser.add_argument("--win-c", default="/mnt/windows", help="Путь монтирования Windows C: (default: /mnt/windows)")
    parser.add_argument("--win-user", default="kosty", help="Имя пользователя в Windows (default: kosty)")
    parser.add_argument("--ai-mount", default="/mnt/ai", help="Точка монтирования диска с AI моделями (default: /mnt/ai)")
    parser.add_argument("--dest-home", default=str(Path.home()), help="Домашняя папка Linux (default: ~)")
    args = parser.parse_args()

    win_gemini = Path(args.win_c) / "Users" / args.win_user / ".gemini"
    win_appdata = Path(args.win_c) / "Users" / args.win_user / "AppData" / "Roaming" / "Antigravity"
    
    dest_gemini = Path(args.dest_home) / ".gemini" / "antigravity"
    dest_config = Path(args.dest_home) / ".gemini" / "config"
    dest_app_config = Path(args.dest_home) / ".config" / "Antigravity"

    print("=" * 65)
    print("  Восстановление проектов и чатов Antigravity на Linux")
    print("=" * 65)

    if not win_gemini.exists():
        print(f"[!] ОШИБКА: Папка Windows .gemini не найдена по пути: {win_gemini}")
        print("    Убедись, что диск Windows C: смонтирован. Например:")
        print("    sudo mkdir -p /mnt/windows && sudo mount -t ntfs3 -o ro /dev/nvme0n1p2 /mnt/windows")
        sys.exit(1)

    # 1. Создаем нужные директории
    print(f"\n[1/6] Подготовка директорий в {args.dest_home}...")
    dest_gemini.mkdir(parents=True, exist_ok=True)
    (dest_gemini / "brain").mkdir(parents=True, exist_ok=True)
    (dest_gemini / "conversations").mkdir(parents=True, exist_ok=True)
    dest_config.mkdir(parents=True, exist_ok=True)
    dest_app_config.mkdir(parents=True, exist_ok=True)

    # 2. Перенос и пропатчивание conversation_summaries.db
    print("\n[2/6] Перенос и обновление путей в conversation_summaries.db...")
    src_db = win_gemini / "antigravity" / "conversation_summaries.db"
    target_db = dest_gemini / "conversation_summaries.db"

    if src_db.exists():
        shutil.copy2(src_db, target_db)
        
        # Копируем WAL/SHM если есть
        src_wal = win_gemini / "antigravity" / "conversation_summaries.db-wal"
        src_shm = win_gemini / "antigravity" / "conversation_summaries.db-shm"
        if src_wal.exists():
            shutil.copy2(src_wal, dest_gemini / "conversation_summaries.db-wal")
        if src_shm.exists():
            shutil.copy2(src_shm, dest_gemini / "conversation_summaries.db-shm")

        # Открываем SQLite и заменяем пути
        conn = sqlite3.connect(str(target_db))
        cursor = conn.cursor()

        # Checkpoint WAL если скопировался
        try:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception as e:
            print(f"    (wal_checkpoint: {e})")

        # Замена путей E:\AI-Dubbing -> /mnt/ai/AI-Dubbing
        ai_linux_uri = f"file://{args.ai_mount}/AI-Dubbing"
        cursor.execute("""
            UPDATE conversation_summaries 
            SET workspace_uris = REPLACE(REPLACE(workspace_uris, 'file:///e%3A/AI-Dubbing', ?), 'file:///e:/AI-Dubbing', ?)
            WHERE workspace_uris LIKE '%AI-Dubbing%'
        """, (f'["{ai_linux_uri}"]', f'["{ai_linux_uri}"]'))
        patched_convs = cursor.rowcount

        # Обновляем также в таблице полнотекстового поиска FTS если есть
        try:
            cursor.execute("""
                UPDATE conversations_fts 
                SET workspace = REPLACE(REPLACE(workspace, 'file:///e%3A/AI-Dubbing', ?), 'file:///e:/AI-Dubbing', ?)
                WHERE workspace LIKE '%AI-Dubbing%'
            """, (ai_linux_uri, ai_linux_uri))
        except Exception:
            pass

        conn.commit()

        # Проверяем количество чатов в проекте дубляжа
        dubbing_count = cursor.execute("""
            SELECT count(*) FROM conversation_summaries 
            WHERE project_id = '014e044f-f32a-4873-86b7-43a6ea42eadd'
        """).fetchone()[0]

        print(f"    [✓] Пути в базе обновлены на: {ai_linux_uri}")
        print(f"    [✓] Найдено и привязано чатов дубляжа: {dubbing_count}")
        conn.close()
    else:
        print("    [!] conversation_summaries.db не найден на Windows")

    # 3. Перенос conversations/*.db
    print("\n[3/6] Копирование баз разговоров (conversations/*.db)...")
    src_convs_dir = win_gemini / "antigravity" / "conversations"
    if src_convs_dir.exists():
        count = 0
        for f in src_convs_dir.glob("*.db"):
            shutil.copy2(f, dest_gemini / "conversations" / f.name)
            count += 1
        print(f"    [✓] Скопировано {count} файлов баз разговоров")

    # 4. Перенос brain/* (папки чатов)
    print("\n[4/6] Копирование историй и логов чатов (brain/*)...")
    src_brain = win_gemini / "antigravity" / "brain"
    if src_brain.exists():
        count = 0
        for item in src_brain.iterdir():
            target_item = dest_gemini / "brain" / item.name
            if item.is_dir() and not target_item.exists():
                shutil.copytree(item, target_item)
                count += 1
            elif item.is_file() and not target_item.exists():
                shutil.copy2(item, target_item)
        print(f"    [✓] Скопировано {count} директорий чатов в brain")

    # 5. Перенос app_storage.json в ~/.config/Antigravity/ (для GUI-проектов)
    print("\n[5/6] Настройка боковой панели проектов в GUI...")
    src_app_storage = win_appdata / "app_storage.json"
    target_app_storage = dest_app_config / "app_storage.json"

    if src_app_storage.exists():
        try:
            with open(src_app_storage, 'r', encoding='utf-8') as fp:
                storage_data = json.load(fp)

            # Сохраняем порядок проектов и выбранный проект
            # Заменяем Windows-пути в файле конфигурации
            raw_text = json.dumps(storage_data, ensure_ascii=False)
            raw_text = raw_text.replace("file:///e%3A/AI-Dubbing", f"file://{args.ai_mount}/AI-Dubbing")
            raw_text = raw_text.replace("file:///e:/AI-Dubbing", f"file://{args.ai_mount}/AI-Dubbing")

            with open(target_app_storage, 'w', encoding='utf-8') as fp:
                fp.write(raw_text)

            print(f"    [✓] Настройки GUI-проектов успешно перенесены в {target_app_storage}")
        except Exception as e:
            print(f"    [!] Предупреждение при переносе app_storage.json: {e}")
            shutil.copy2(src_app_storage, target_app_storage)
    else:
        print("    [!] app_storage.json не найден в Windows AppData")

    # 6. Перенос скиллов, knowledge, state
    print("\n[6/6] Копирование кастомизаций, скиллов и состояния...")
    for item in ["knowledge", "antigravity_state.pbtxt", "installation_id"]:
        src_item = win_gemini / "antigravity" / item
        if src_item.exists():
            target_item = dest_gemini / item
            if src_item.is_dir() and not target_item.exists():
                shutil.copytree(src_item, target_item)
            elif src_item.is_file():
                shutil.copy2(src_item, target_item)
            print(f"    [✓] Скопирован {item}")

    src_config = win_gemini / "config"
    if src_config.exists():
        for item in src_config.iterdir():
            target_item = dest_config / item.name
            if item.is_dir() and not target_item.exists():
                shutil.copytree(item, target_item)
            elif item.is_file() and not target_item.exists():
                shutil.copy2(item, target_item)
        print("    [✓] Скопированы пользовательские скиллы и правила")

    print("\n" + "=" * 65)
    print("  ГОТОВО! Все чаты и проект дубляжа восстановлены.")
    print("  Теперь запустите Antigravity:")
    print("    antigravity")
    print("=" * 65)

if __name__ == "__main__":
    main()
