#!/usr/bin/env python3
import os
import time
import signal
import logging
import RPi.GPIO as GPIO

# === КОНФИГУРАЦИЯ ===
FAN_PIN = 21
TEMP_ON = 60.0
TEMP_OFF = 50.0
CHECK_INTERVAL = 5

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("fan_control")


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0
    except Exception as e:
        logger.error(f"Не удалось прочитать температуру: {e}")
        return None


def cleanup(signum=None, frame=None):
    logger.info("Получен сигнал завершения. Остановка вентилятора и очистка GPIO...")
    try:
        GPIO.output(FAN_PIN, GPIO.LOW)
        GPIO.cleanup()
    except Exception:
        pass
    os._exit(0)


def main():
    # Инициализация GPIO внутри main
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN, GPIO.OUT)
    GPIO.output(FAN_PIN, GPIO.LOW)

    fan_is_on = False  # Локальная переменная

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    logger.info(
        f"Скрипт запущен. GPIO{FAN_PIN} | Вкл: {TEMP_ON}°C | Выкл: {TEMP_OFF}°C"
    )

    while True:
        temp = get_cpu_temp()
        if temp is None:
            time.sleep(CHECK_INTERVAL)
            continue

        if not fan_is_on and temp >= TEMP_ON:
            GPIO.output(FAN_PIN, GPIO.HIGH)
            fan_is_on = True
            logger.info(
                f" Температура {temp:.1f}°C >= {TEMP_ON}°C → ВЕНТИЛЯТОР ВКЛЮЧЁН"
            )

        elif fan_is_on and temp <= TEMP_OFF:
            GPIO.output(FAN_PIN, GPIO.LOW)
            fan_is_on = False
            logger.info(
                f" Температура {temp:.1f}°C <= {TEMP_OFF}°C → ВЕНТИЛЯТОР ВЫКЛЮЧЕН"
            )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        cleanup()
