# Инструкции для AI-агента: Настройка Linux после установки

## Контекст

Этот репозиторий содержит план миграции с Windows на dual-boot Linux (Ubuntu 24.04)
для разблокировки тензорных ядер RTX 3070 через gpu-unlock.

Полный пошаговый план — в [PLAN.md](PLAN.md).

## Конфигурация машины

- **GPU:** NVIDIA GeForce RTX 3070, 8 GB
- **RAM:** 32 GB
- **ОС (dual-boot):** Windows 11 Pro + Ubuntu 24.04 LTS
- **Диск с моделями (NTFS):** бывший `E:\` — label `Other SATA`, содержит `AI-Dubbing/`
- **Диск Windows (NTFS):** бывший `C:\` — label `System`, содержит `.gemini/` с данными Antigravity

## Задача агента

После чистой установки Ubuntu выполнить автоматическую настройку системы.
Используй скрипт `setup.sh` как основу, но адаптируй под текущее состояние.

### Порядок действий (этапы 3–6 из PLAN.md)

### Этап 3: Базовая настройка

1. Обновить систему: `sudo apt update && sudo apt upgrade -y`
2. Установить NVIDIA драйвер: `sudo apt install -y nvidia-driver-560`
3. Найти NTFS-раздел с label `Other SATA` (бывший `E:\`) и смонтировать в `/mnt/ai` (read-only)
4. Добавить запись в `/etc/fstab` для автомонтирования (по UUID, `ntfs3`, `ro,nofail`)
5. Создать симлинк: `~/AI-Dubbing` → `/mnt/ai/AI-Dubbing`

### Этап 4: GPU Unlock

1. Установить зависимости: `git build-essential dkms linux-headers-$(uname -r)`
2. Склонировать `https://github.com/Zagitta/gpu-unlock`
3. Собрать и установить: `make install`
4. Добавить `gpu_unlock.targets=all` в `GRUB_CMDLINE_LINUX_DEFAULT` в `/etc/default/grub`
5. Выполнить `sudo update-grub`

### Этап 5: Antigravity + перенос данных

1. Установить Antigravity: `curl -sL https://antigravity.google/install.sh | bash`
2. Смонтировать раздел Windows `C:` (label `System`) в `/mnt/windows` (read-only)
3. Перенести данные Antigravity:
   - `brain/*` → `~/.gemini/antigravity/brain/` (121 чат)
   - `conversation_summaries.db` → `~/.gemini/antigravity/`
   - `conversations/*` → `~/.gemini/antigravity/conversations/`
   - `knowledge/*` → `~/.gemini/antigravity/knowledge/`
   - `config/*` → `~/.gemini/config/`
4. **НЕ копировать:** `google_auth/`, `bin/`, `lib/`, `builtin/`, `daemon/`
5. Попросить пользователя авторизоваться: `agy`

### Этап 6: CosyVoice3

1. Установить: `python3 python3-pip python3-venv ffmpeg`
2. Создать venv: `python3 -m venv ~/cosyvoice-env`
3. Установить PyTorch с CUDA: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121`
4. Установить CosyVoice по инструкциям из их репозитория
5. Модели указывать из `~/AI-Dubbing/`

### Финальная проверка

1. `nvidia-smi` — RTX 3070 видна
2. `ls ~/AI-Dubbing/` — модели доступны
3. `agy` — Antigravity работает, старые чаты видны
4. После перезагрузки: `journalctl -k -b | grep gpu_unlock` — unlock успешен

## Важные ограничения

- Все NTFS-разделы монтировать **read-only** (`ro`)
- **Не трогать** разделы Windows (C:, P:, M:, E:)
- **Не копировать** `google_auth` — пользователь авторизуется сам
- Перед `sudo reboot` всегда предупреждать пользователя
- При ошибках gpu-unlock — проверить `dmesg` и `journalctl -k`
