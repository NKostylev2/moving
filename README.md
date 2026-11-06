# moving

Миграция Windows → Dual-boot Linux (Ubuntu 24.04) для RTX 3070 GPU Unlock.

## Что внутри

| Файл | Описание |
|---|---|
| [PLAN.md](PLAN.md) | Пошаговый план на русском — от подготовки Windows до работающей системы |
| [AGENTS.md](AGENTS.md) | Инструкции для AI-агента (Antigravity) по автонастройке |
| [setup.sh](setup.sh) | Интерактивный скрипт полной автонастройки |
| [fix_antigravity_migration.py](fix_antigravity_migration.py) | Скрипт восстановления проектов, чатов и обновления путей с Windows на Linux |
| [bench_cosyvoice.py](bench_cosyvoice.py) | Скрипт бенчмарка CosyVoice 3 (RTF, скорость) с авто-сравнением Windows vs Linux |
| [bench_report_windows.json](bench_report_windows.json) | Исходный baseline-замер производительности на Windows (RTX 3070, RTF 1.182) |

## Быстрый старт (после установки Ubuntu)

```bash
git clone https://github.com/NKostylev2/moving
cd moving
chmod +x setup.sh
sudo ./setup.sh
```

### Если Ubuntu уже установлена, но проект дубляжа не отобразился:

```bash
cd moving
git pull

# Смонтировать Windows C: (если не смонтирован)
sudo mkdir -p /mnt/windows
sudo mount -t ntfs3 -o ro /dev/nvme0n1p2 /mnt/windows

# Запустить восстановление проектов и чатов
python3 fix_antigravity_migration.py --win-c /mnt/windows --ai-mount /mnt/ai
```

Скрипт интерактивный — спрашивает перед каждым действием.

## Бенчмарк производительности (CosyVoice 3)

До миграции был снят baseline на Windows 11 (RTX 3070):
- **Модель:** `Fun-CosyVoice3-0.5B`
- **Загрузка модели:** 22.75 сек
- **Средний RTF:** 1.1818 (0.846x от реального времени)
- **Файл отчёта:** [bench_report_windows.json](bench_report_windows.json)

После настройки CosyVoice3 на Linux:
```bash
source ~/cosyvoice-env/bin/activate
python3 bench_cosyvoice.py
```
Скрипт автоматически сравнит полученные значения с Windows baseline и выведет таблицу прироста скорости от GPU Unlock.

## Или через Antigravity

Если Antigravity уже установлен:

```
Настрой систему по инструкциям из ~/moving/AGENTS.md
```

## Конфигурация

- **GPU:** NVIDIA GeForce RTX 3070, 8 GB
- **RAM:** 32 GB
- **Модели:** `E:\AI-Dubbing` → `/mnt/ai/AI-Dubbing`
- **Цель:** +15–30% скорость CosyVoice3 через gpu-unlock
