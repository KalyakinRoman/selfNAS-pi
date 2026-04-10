# selfNAS-pi

Проект по созданию собственного сетевого хранилища (NAS) на базе Raspberry Pi для домашнего использования.
Репозиторий содержит инструкции, конфигурации и Docker-артефакты для развертывания и поддержки системы.

## Цель проекта

Создать простой, автономный и расширяемый домашний NAS, который позволяет:

* хранить файлы централизованно;
* передавать данные по локальной сети и Wi-Fi;
* использовать недорогое и энергоэффективное оборудование;
* управлять сервисами через Docker;
Проект ориентирован на homelab / self-hosted сценарии

## Оборудование
| Короткое название | Суть | На основе чего | Зачем нужно |
|------------------|------|---------------|-------------|
| CoreNode | Сервер | Raspberry Pi 4 Model B (4 GB RAM) | Центральный узел NAS, запуск Docker и сервисов |
| PowerUnit | Питание | AC 240V → DC 5V 3A (DSM-0530) | Стабильное питание сервера |
| BootMedia | Системная память | microSD 32 GB | ОС, загрузка и базовые конфигурации |
| DataVault | Хранилище данных | Portable SSD KODAK X200 1 TB | Основное файловое хранилище |
| NetLink | Сеть | Ethernet ↔ Ethernet кабель | Подключение к модему / роутеру |


## Настройка
Подготовка Raspberry Pi для SelfNAS-Pi с нуля
1. Очистка SD-карты
SD Card Formatter - 5
2. Настройка системы
Через Raspberry Pi Imager 2.0.6
Установлена Raspberry Pi OS 64-bit

## Подключение
0. Вставить кабель питания и ethernet в Raspberry Pi. Включить.
1. Команда доступа ssh USER@IP. Пример: ssh user_snas@192.168.0.101

* В файле `.env` указаны credential для доступа
* В роутере закреплён **статический IP** для Raspberry Pi (DHCP/Резервирование адресов)

## Настройка докер
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo usermod -aG docker $USER
newgrp docker


## Форматирование диска
sudo umount /media/user_snas/KODAK
sudo mkfs.ext4 /dev/sda2


## Подготовка накопителя
sudo mkdir -p /mnt/nas
sudo mount /dev/sda2 /mnt/nas
sudo chown -R user_snas:user_snas /mnt/nas
sudo chmod -R 755 /mnt/nas
sudo blkid /dev/sda2 -> UUID
sudo nano /etc/fstab -> добавить /dev/sda2: UUID="XXXX-XXXX" TYPE="ext4"
systemctl daemon-reload
mkdir -p /mnt/nas/{data,media,backups,configs}

Структура /mnt/nas
```
/mnt/nas $ ls -la
drwxr-xr-x 2 root      root       4096 Feb 15 17:05 backups
drwxr-xr-x 2 root      root       4096 Feb 15 17:04 configs
drwxr-xr-x 2 root      root       4096 Feb 15 17:04 data
drwxr-xr-x 2 root      root       4096 Feb 15 17:05 media
```


## Grams
cd /opt/grampsweb

docker compose up -d

## Настройка SWAP

sudo mkdir -p /mnt/nas/swap
sudo fallocate -l 4G /mnt/nas/swap/swapfile
sudo chmod 600 /mnt/nas/swap/swapfile
sudo mkswap /mnt/nas/swap/swapfile
sudo swapon /mnt/nas/swap/swapfile
sudo nano /etc/fstab
Файл:
```
proc            /proc           proc    defaults          0       0
PARTUUID=651f9ef0-01  /boot/firmware  vfat    defaults          0       2       
PARTUUID=651f9ef0-02  /               ext4    defaults,noatime  0       1       
UUID=e1b46230-a29e-4f6b-ade4-c1d5b2df9897  /mnt/nas  ext4  defaults,nofail  0  2
/mnt/nas/swap/swapfile none swap sw 0 0
```
cat /proc/sys/vm/swappiness

echo -e "\n# Optimized for zram + SSD swap (PhotoPrism on RPi)\nvm.swappiness=100\nvm.vfs_cache_pressure=50\nvm.watermark_scale_factor=200" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p


## Копирование

rsync -avh --progress --ignore-existing /media/user_snas/BE44BD9A44BD563D/Фото /mnt/nas/media/photos/
rsync -avh --progress --ignore-existing /mnt/nas/media/photos/ /media/user_snas/BE44BD9A44BD563D/


## Вентилятор

https://www.youtube.com/watch?v=h8BfSWJH9l0

Управление вентилятором через транзистор 2N2222 и GPIO Raspberry Pi
Схема подключения:
Красный провод вентилятора → +5V питания
Чёрный провод вентилятора → Коллектор (C) транзистора 2N2222
Эмиттер (E) транзистора → GND
База (B) транзистора → GPIO 21 через резистор 340 Ом

Принцип работы:
GPIO 21 управляет открытием транзистора.
При сигнале HIGH (3.3V) транзистор открывается, вентилятор включается.
При сигнале LOW транзистор закрывается, вентилятор выключается.

Примечания:
Использование резистора 340 Ом обеспечивает достаточный ток базы для надёжного открытия транзистора при токе вентилятора до 200 мА.

У транзистора при взгляде на плоскую сторону
Ножка 1 — Эмиттер
Ножка 2 — База
Ножка 3 — Коллектор


## Автоматическое управление вентилятором

Скрипт `fan_control.py` регулирует охлаждение на основе температуры CPU с защитой от частых переключений (гистерезис). Работает как фоновая служба systemd.

### Принцип работы
- **Включение**: при температуре `≥ 60°C`
- **Выключение**: при падении до `≤ 50°C`
- **Проверка**: каждые 5 секунд
- **Логирование**: `journalctl -u fan-control.service`

### Настройка порогов
Отредактируйте константы в начале `/opt/scripts/fan_control.py`:
```python
TEMP_ON = 60.0   # °C (включение)
TEMP_OFF = 50.0  # °C (выключение)
CHECK_INTERVAL = 5  # сек

После правки перезапустите службу: 

```bash
sudo systemctl restart fan-control.service

# Текущий статус
systemctl status fan-control.service

# Логи в реальном времени
journalctl -u fan-control.service -f

# Временное отключение (без удаления службы)
sudo systemctl stop fan-control.service

# Температура
vcgencmd measure_temp
```

### Важные заметки
1. **Гистерезис**: разрыв `10°C` между включением и выключением гарантирует, что вентилятор не будет "дёргаться" при температуре около порога.
2. **Автозапуск**: `Restart=always` в службе перезапустит скрипт при сбое, а `enable` гарантирует загрузку после ребута.
3. **Безопасность**: при остановке службы или перезагрузке скрипт всегда подаёт `LOW` на GPIO и очищает пины через `GPIO.cleanup()`, предотвращая случайное включение вентилятора.
4. **Совместимость**: если используете Raspberry Pi OS Bookworm и `RPi.GPIO` вызывает предупреждения, замените `import RPi.GPIO as GPIO` на `from gpiozero import LED` и замените `GPIO.output(FAN_PIN, GPIO.HIGH)` на `fan = LED(21); fan.on()` (логика останется идентичной).

Скрипт готов к работе. Если нужно добавить отправку алертов в Telegram/Matrix или интеграцию с `telegraf`/`Prometheus` — напишите, добавлю блок мониторинга.

### Выключение устройства

```bash
# По сети (через SSH)
ssh user_snas@selfnas 'sudo shutdown -h now'

# Или создайте алиас в ~/.bashrc:
alias nas-off='ssh user_snas@selfnas "sudo shutdown -h now"'