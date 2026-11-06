#!/usr/bin/env bash
# ============================================================================
# setup.sh — Автонастройка Ubuntu после установки dual-boot
# Для RTX 3070 + gpu-unlock + Antigravity + CosyVoice3
#
# Использование:
#   chmod +x setup.sh
#   sudo ./setup.sh
#
# Скрипт интерактивный: спрашивает перед каждым этапом.
# После gpu-unlock потребуется перезагрузка.
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }

ask() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    read -rp "Продолжить? (y/n): " answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

if [[ $EUID -ne 0 ]]; then
    err "Запусти с sudo: sudo ./setup.sh"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Настройка Linux: RTX 3070 GPU Unlock + Antigravity       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
info "Пользователь: $REAL_USER"
info "Домашняя папка: $REAL_HOME"
echo ""

# ============================================================================
# ЭТАП 3.1: Обновление системы
# ============================================================================
if ask "Этап 3.1: Обновить систему (apt update && upgrade)"; then
    apt update && apt upgrade -y
    log "Система обновлена"
fi

# ============================================================================
# ЭТАП 3.2: NVIDIA драйвер
# ============================================================================
if ask "Этап 3.2: Установить NVIDIA драйвер (nvidia-driver-560)"; then
    apt install -y nvidia-driver-560
    log "NVIDIA драйвер установлен"
    warn "Перезагрузка нужна позже (не сейчас)"
fi

# ============================================================================
# ЭТАП 3.3: Монтирование диска E: (AI-Dubbing)
# ============================================================================
if ask "Этап 3.3: Подключить диск с моделями (AI-Dubbing)"; then
    # Найти раздел с label "Other SATA"
    AI_DEV=""
    AI_UUID=""
    while IFS= read -r line; do
        dev=$(echo "$line" | awk '{print $1}')
        label=$(blkid -s LABEL -o value "/dev/$dev" 2>/dev/null || true)
        if [[ "$label" == "Other SATA" ]]; then
            AI_DEV="/dev/$dev"
            AI_UUID=$(blkid -s UUID -o value "$AI_DEV")
            break
        fi
    done < <(lsblk -rno NAME,FSTYPE | grep ntfs)

    if [[ -z "$AI_DEV" ]]; then
        # Показать все NTFS разделы для ручного выбора
        warn "Раздел 'Other SATA' не найден автоматически"
        info "NTFS разделы:"
        lsblk -o NAME,SIZE,LABEL,FSTYPE | grep -i ntfs
        read -rp "Введи устройство (например sda3): " manual_dev
        AI_DEV="/dev/$manual_dev"
        AI_UUID=$(blkid -s UUID -o value "$AI_DEV")
    fi

    info "Найден раздел: $AI_DEV (UUID=$AI_UUID)"

    mkdir -p /mnt/ai
    mount -t ntfs3 -o ro "$AI_DEV" /mnt/ai

    if ls /mnt/ai/AI-Dubbing/ &>/dev/null; then
        log "Модели найдены в /mnt/ai/AI-Dubbing/"
    else
        warn "Папка AI-Dubbing не найдена — проверь вручную: ls /mnt/ai/"
    fi

    # Добавить в fstab
    if ! grep -q "$AI_UUID" /etc/fstab; then
        echo "UUID=$AI_UUID  /mnt/ai  ntfs3  ro,nofail  0  0" >> /etc/fstab
        log "Добавлено в /etc/fstab (автомонтирование)"
    else
        info "Уже есть в /etc/fstab"
    fi

    # Симлинк
    sudo -u "$REAL_USER" ln -sfn /mnt/ai/AI-Dubbing "$REAL_HOME/AI-Dubbing"
    log "Симлинк: ~/AI-Dubbing → /mnt/ai/AI-Dubbing"
fi

# ============================================================================
# ЭТАП 4: GPU Unlock
# ============================================================================
if ask "Этап 4: Установить GPU Unlock для RTX 3070"; then
    apt install -y git build-essential dkms "linux-headers-$(uname -r)"

    UNLOCK_DIR="$REAL_HOME/gpu-unlock"
    if [[ -d "$UNLOCK_DIR" ]]; then
        info "gpu-unlock уже склонирован"
    else
        sudo -u "$REAL_USER" git clone https://github.com/Zagitta/gpu-unlock "$UNLOCK_DIR"
    fi

    cd "$UNLOCK_DIR"
    make install
    log "gpu-unlock установлен"

    # Параметр ядра
    GRUB_FILE="/etc/default/grub"
    if grep -q "gpu_unlock.targets" "$GRUB_FILE"; then
        info "gpu_unlock.targets уже в GRUB"
    else
        sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 gpu_unlock.targets=all"/' "$GRUB_FILE"
        log "gpu_unlock.targets=all добавлен в GRUB"
    fi

    update-grub
    log "GRUB обновлён"
    warn "Нужна перезагрузка для активации unlock (позже)"
fi

# ============================================================================
# ЭТАП 5: Antigravity
# ============================================================================
if ask "Этап 5: Установить Antigravity"; then
    sudo -u "$REAL_USER" bash -c 'curl -sL https://antigravity.google/install.sh | bash'
    log "Antigravity установлен"
fi

# ============================================================================
# ЭТАП 5.2: Перенос данных Antigravity с Windows
# ============================================================================
if ask "Этап 5.2: Перенести чаты, проекты и настройки Antigravity с Windows"; then
    # Монтирование C:
    WIN_DEV=""
    WIN_UUID=""
    while IFS= read -r line; do
        dev=$(echo "$line" | awk '{print $1}')
        label=$(blkid -s LABEL -o value "/dev/$dev" 2>/dev/null || true)
        if [[ "$label" == "System" ]]; then
            WIN_DEV="/dev/$dev"
            WIN_UUID=$(blkid -s UUID -o value "$WIN_DEV")
            break
        fi
    done < <(lsblk -rno NAME,FSTYPE | grep ntfs)

    if [[ -z "$WIN_DEV" ]]; then
        warn "Раздел 'System' не найден"
        info "NTFS разделы:"
        lsblk -o NAME,SIZE,LABEL,FSTYPE | grep -i ntfs
        read -rp "Введи устройство с Windows C: (например nvme0n1p2): " manual_dev
        WIN_DEV="/dev/$manual_dev"
    fi

    mkdir -p /mnt/windows
    mount -t ntfs3 -o ro "$WIN_DEV" /mnt/windows
    info "Windows смонтирован в /mnt/windows"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$SCRIPT_DIR/fix_antigravity_migration.py" ]]; then
        sudo -u "$REAL_USER" python3 "$SCRIPT_DIR/fix_antigravity_migration.py" \
            --win-c /mnt/windows \
            --ai-mount /mnt/ai \
            --dest-home "$REAL_HOME"
    else
        err "fix_antigravity_migration.py не найден в $SCRIPT_DIR"
    fi

    umount /mnt/windows 2>/dev/null || true
fi

# ============================================================================
# ЭТАП 6: Python / CosyVoice3 зависимости
# ============================================================================
if ask "Этап 6: Установить Python и зависимости для CosyVoice3"; then
    apt install -y python3 python3-pip python3-venv ffmpeg

    sudo -u "$REAL_USER" python3 -m venv "$REAL_HOME/cosyvoice-env"
    sudo -u "$REAL_USER" bash -c "source $REAL_HOME/cosyvoice-env/bin/activate && pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121"
    log "Python venv + PyTorch + CUDA установлены"
    info "Активация: source ~/cosyvoice-env/bin/activate"
    info "Далее установи CosyVoice по их инструкциям, модели в ~/AI-Dubbing/"
fi

# ============================================================================
# ФИНАЛ
# ============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Настройка завершена!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
info "Что осталось:"
echo "  1. Перезагрузиться: sudo reboot"
echo "  2. Проверить unlock: journalctl -k -b | grep gpu_unlock"
echo "  3. Проверить GPU: nvidia-smi"
echo "  4. Авторизоваться в Antigravity: agy"
echo "  5. Установить CosyVoice3 в ~/cosyvoice-env"
echo ""
read -rp "Перезагрузить сейчас? (y/n): " do_reboot
if [[ "$do_reboot" =~ ^[Yy]$ ]]; then
    reboot
fi
