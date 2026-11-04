# Пошаговый план: Dual-boot Linux + GPU Unlock + Antigravity

## Твоя система

| Параметр | Значение |
|---|---|
| ОС | Windows 11 Pro (UEFI, GPT) |
| GPU | **NVIDIA GeForce RTX 3070, 8 GB** |
| RAM | 32 GB |
| Диск 0 (P3-256, 238 ГБ) | `E:` — AI-Dubbing (модели, 80 ГБ свободно) + EFI раздел |
| Диск 1 (XPG GAMMIX S60, 1.9 ТБ) | `C:` (21 ГБ своб.), `P:` (69 ГБ своб.), `M:` (432 ГБ своб.) |

> [!IMPORTANT]
> Linux ставим в **80 ГБ**, отщипнутых от раздела `M:`. Диск `E:` с моделями не трогаем.

---

## Этап 1: Подготовка в Windows (30 мин)

### 1.1. Отключить Fast Startup

Без этого Linux не сможет нормально читать NTFS-разделы.

1. **Win+R** → `powercfg.cpl` → Enter
2. Слева: **«Действия кнопок питания»**
3. Нажать **«Изменение параметров, которые сейчас недоступны»**
4. Снять галку **«Включить быстрый запуск»**
5. Сохранить

### 1.2. Сжать раздел M: для Linux

1. **Win+R** → `diskmgmt.msc` → Enter
2. Правый клик по разделу **M: (Main)** → **«Сжать том»**
3. Указать размер: **81920 МБ** (80 ГБ)
4. Нажать **«Сжать»**

Появится нераспределённое пространство. **Не форматировать** — установщик Linux сделает сам.

### 1.3. Скачать Ubuntu 24.04 LTS

https://ubuntu.com/download/desktop

### 1.4. Записать загрузочную флешку

Нужна USB-флешка ≥ 4 ГБ + [Rufus](https://rufus.ie):

1. Выбрать флешку и ISO
2. Схема раздела: **GPT**
3. Целевая система: **UEFI**
4. **Старт**

---

## Этап 2: Установка Ubuntu (20 мин)

### 2.1. Загрузка с флешки

1. Перезагрузить ПК
2. **F8 / F11 / F12 / Del** → меню загрузки
3. Выбрать **USB UEFI**
4. **«Try or Install Ubuntu»**

### 2.2. Установка

1. Язык, клавиатура — по желанию
2. Тип установки → **«Другой вариант» (ручная разметка)**

Работай **только** с нераспределённым пространством на Диске 1:

| Точка монтирования | Размер | Файловая система |
|---|---|---|
| `/` | 72 ГБ | ext4 |
| `swap` | 8 ГБ | swap |
| Загрузчик | Устройство с EFI-разделом (Диск 0) | — |

> [!CAUTION]
> **Не трогай существующие разделы!** C:, P:, M:, E: — оставить как есть.

3. Создать пользователя и пароль
4. Установить → перезагрузить → вытащить флешку

### 2.3. Проверка dual-boot

После перезагрузки — **меню GRUB**:
- Ubuntu ✅
- Windows Boot Manager ✅

Проверь, что обе системы загружаются.

---

## Этап 3: Базовая настройка Linux (15 мин)

### 3.1. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2. Установить NVIDIA драйвер

```bash
sudo apt install -y nvidia-driver-560
sudo reboot
```

Проверить:
```bash
nvidia-smi   # должна показать RTX 3070
```

### 3.3. Подключить диск E: с моделями

```bash
# Найти раздел E:
lsblk -f | grep ntfs

# Создать точку монтирования
sudo mkdir /mnt/ai

# Узнать UUID
sudo blkid | grep ntfs
# Найти строку с LABEL="Other SATA" — это E:

# Добавить в fstab для автомонтирования
sudo nano /etc/fstab
```

Добавить строку (заменить UUID на реальный):
```
UUID=XXXX-XXXX  /mnt/ai  ntfs3  ro,nofail  0  0
```

Применить и проверить:
```bash
sudo mount -a
ls /mnt/ai/AI-Dubbing/   # должны быть твои модели
```

Симлинк для удобства:
```bash
ln -s /mnt/ai/AI-Dubbing ~/AI-Dubbing
```

---

## Этап 4: GPU Unlock (5 мин)

### 4.1. Зависимости для сборки

```bash
sudo apt install -y git build-essential dkms linux-headers-$(uname -r)
```

### 4.2. Сборка и установка

```bash
git clone https://github.com/Zagitta/gpu-unlock
cd gpu-unlock
make install
```

### 4.3. Параметр ядра

```bash
sudo nano /etc/default/grub
```

Изменить строку:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash gpu_unlock.targets=all"
```

Сохранить (Ctrl+O → Enter → Ctrl+X), затем:
```bash
sudo update-grub
sudo reboot
```

### 4.4. Проверить

```bash
journalctl -k -b | grep gpu_unlock
```

Должно быть сообщение об успешном unlock RTX 3070.

---

## Этап 5: Antigravity + перенос чатов (10 мин)

### 5.1. Установить Antigravity

```bash
curl -sL https://antigravity.google/install.sh | bash
```

Запустить и авторизоваться:
```bash
agy
# Следовать инструкциям для входа через Google
```

Закрыть после авторизации (Ctrl+D Ctrl+D).

### 5.2. Смонтировать диск C: (если ещё не смонтирован)

```bash
sudo mkdir /mnt/windows
sudo mount -t ntfs3 -o ro /dev/nvme0n1p2 /mnt/windows
```

Проверить:
```bash
ls /mnt/windows/Users/kosty/.gemini/antigravity/brain/ | head
```

### 5.3. Перенести данные (121 чат, ~2 ГБ)

```bash
# История чатов
cp -r /mnt/windows/Users/kosty/.gemini/antigravity/brain/* \
      ~/.gemini/antigravity/brain/

# База саммари чатов
cp /mnt/windows/Users/kosty/.gemini/antigravity/conversation_summaries.db \
   ~/.gemini/antigravity/

# Индекс разговоров
cp -r /mnt/windows/Users/kosty/.gemini/antigravity/conversations/* \
      ~/.gemini/antigravity/conversations/

# Learned знания
cp -r /mnt/windows/Users/kosty/.gemini/antigravity/knowledge/* \
      ~/.gemini/antigravity/knowledge/

# Кастомизации (скиллы, правила)
cp -r /mnt/windows/Users/kosty/.gemini/config/* \
      ~/.gemini/config/
```

> [!NOTE]
> Авторизацию (`google_auth`) копировать **не нужно** — ты уже залогинился на шаге 5.1. Бинарники (`bin`, `lib`, `builtin`) тоже не копируем — у Linux свои.

### 5.4. Проверить

```bash
agy
# Должны быть видны старые чаты и кастомизации
```

---

## Этап 6: CosyVoice3 (15 мин)

```bash
# Python и зависимости
sudo apt install -y python3 python3-pip python3-venv ffmpeg

# Виртуальное окружение
python3 -m venv ~/cosyvoice-env
source ~/cosyvoice-env/bin/activate

# PyTorch с CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Установить CosyVoice (следуй их инструкциям)
# Модели указывай из ~/AI-Dubbing/...
```

---

## Итоговая схема

```
Загрузка ПК → GRUB
│
├── Ubuntu
│   ├── gpu_unlock → RTX 3070 на полной скорости (+81% тензоры)
│   ├── CosyVoice3 → +15-30% быстрее генерация речи
│   ├── E:\AI-Dubbing → /mnt/ai/AI-Dubbing (read-only, без перекачки)
│   └── Antigravity → 121 чат + скиллы перенесены
│
└── Windows
    ├── GPU как обычно (заводские настройки)
    └── Antigravity → всё на месте, ничего не изменилось
```

---

## Откат / удаление

| Действие | Как |
|---|---|
| Отключить unlock | Убрать `gpu_unlock.targets=all` из GRUB → `sudo update-grub` |
| Удалить unlock | `sudo apt remove gpu-unlock-dkms` |
| Удалить Linux целиком | В Windows: `diskmgmt.msc` → удалить Linux-разделы → `bootrec /fixboot` из recovery |
| Данные Windows | Ничего не затрагивается — всё read-only |

---

## Чеклист перед началом

- [ ] USB-флешка ≥ 4 ГБ
- [ ] Скачан Ubuntu 24.04 LTS ISO
- [ ] Скачан Rufus
- [ ] Fast Startup отключён
- [ ] Раздел M: сжат на 80 ГБ
- [ ] Знаешь кнопку Boot Menu на материнской плате (F8/F11/F12/Del)
