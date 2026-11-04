# moving

Миграция Windows → Dual-boot Linux (Ubuntu 24.04) для RTX 3070 GPU Unlock.

## Что внутри

| Файл | Описание |
|---|---|
| [PLAN.md](PLAN.md) | Пошаговый план на русском — от подготовки Windows до работающей системы |
| [AGENTS.md](AGENTS.md) | Инструкции для AI-агента (Antigravity) по автонастройке |
| [setup.sh](setup.sh) | Интерактивный скрипт автонастройки |

## Быстрый старт (после установки Ubuntu)

```bash
git clone https://github.com/NKostylev2/moving
cd moving
chmod +x setup.sh
sudo ./setup.sh
```

Скрипт интерактивный — спрашивает перед каждым действием.

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
