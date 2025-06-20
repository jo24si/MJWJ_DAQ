#ver4 RPi-GP40를 사용한 아날로그 입력 읽기 및 CSV 저장 예제 (2보드 확장 버전)
#ver5 IO 출력 입력 기능 추가 250613 sj


import sys
import time
import argparse
import spidev
import RPi.GPIO as GPIO
import os
import csv
from datetime import datetime

# 전압/전류 입력 범위에 대한 설정 테이블
range_names = ["±10V", "±5V", "±2.5V", "±1.25V", "±0.5V", "0-10V", "0-5V", "0-2.5V", "0-1.25V", "0-20mA", "NONE"]
range_registers = [0, 1, 2, 3, 11, 5, 6, 7, 15, 6, 0]
range_offsets = [0x800]*5 + [0x000]*5 + [0x000]
range_scales = [5.00, 2.50, 1.25, 0.625, 0.3125,
                 2.50, 1.25, 0.625, 0.3125, 5.00, 0.0]
# channel_ranges = [0]*8  # (기존)
channel_ranges = [0]*16  # 16채널 대응

# AD_CS_GPIO = 8  # (기존 단일 보드)
AD_CS_GPIO_1 = 8  # 보드1
AD_CS_GPIO_2 = 7  # 보드2
DOUT_GPIO = 12
DIN_GPIO = 13
ISO_PWR_GPIO = 27

INPUT_GPIO_PINS = [5, 17, 27, 22]  # 입력 핀
OUTPUT_GPIO_PINS = [23, 24]        # 출력 핀 (제어 예정, 현재는 주석처리)

spi = spidev.SpiDev()

# RPi-GP40 보드 초기 설정
def init_gp40():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # GPIO.setup(AD_CS_GPIO, GPIO.OUT, initial=GPIO.HIGH)  # (기존)
    GPIO.setup(AD_CS_GPIO_1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(AD_CS_GPIO_2, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ISO_PWR_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(DOUT_GPIO, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
#IO 입력 추가
    for pin in INPUT_GPIO_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    for pin in OUTPUT_GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    time.sleep(0.5)

# SPI 통신 (CS 핀 직접 지정 방식으로 수정됨)
def spi_transfer(data, cs_gpio):
    GPIO.output(cs_gpio, GPIO.LOW)
    result = spi.xfer(data)
    GPIO.output(cs_gpio, GPIO.HIGH)
    return result

# 채널 입력 범위 설정
def set_channel_range(ch, r):
    # real_ch = select_adc_board(ch)  # (기존)
    if ch < 8:
        cs = AD_CS_GPIO_1
        real_ch = ch
    else:
        cs = AD_CS_GPIO_2
        real_ch = ch - 8
    data = [((5 + real_ch) << 1) | 1, r, 0x00, 0x00]
    spi_transfer(data, cs)

# ADC 값 읽기 (보드 전환 방식으로 수정됨)
def read_adc(ch):
    if ch < 8:
        cs = AD_CS_GPIO_1
        real_ch = ch
    else:
        cs = AD_CS_GPIO_2
        real_ch = ch - 8
    cmd = [0xC0 + (real_ch << 2), 0x00, 0x00, 0x00]
    spi_transfer(cmd, cs)
    result = spi_transfer(cmd, cs)
    value = (result[2] << 4) + (result[3] >> 4)
    return value

# 실시간 CSV 기록 함수 (1000Hz 측정 → 1초마다 min/max/avg 저장)
def log_adc_csv():
    now = datetime.now()
    last_hour = now.hour
    csv_file = now.strftime("adc_log_%Y%m%d_%H%M%S.csv")
    f = open(csv_file, 'a', newline='')
    writer = csv.writer(f)

    # buffers = [[] for _ in range(8)]  # (기존)
    buffers = [[] for _ in range(16)]
    start_time = time.perf_counter()

    try:
        while True:
            now = datetime.now()
            if now.hour != last_hour:
                f.close()
                csv_file = now.strftime("adc_log_%Y%m%d_%H%M%S.csv")
                f = open(csv_file, 'a', newline='')
                writer = csv.writer(f)
                last_hour = now.hour

            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 1.0:
                # for ch in range(8):  # (기존)
                for ch in range(16):
                    if channel_ranges[ch] <= 9:
                        raw = read_adc(ch)
                        val = (raw - range_offsets[channel_ranges[ch]]) * range_scales[channel_ranges[ch]] / 1000
                        buffers[ch].append(val)
                    else:
                        buffers[ch].append(None)
                time.sleep(0.001)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")[:-3]
            row = [timestamp]
            for ch_buf in buffers:
                valid_values = [v for v in ch_buf if v is not None]
                if valid_values:
                    #row.append(f"{min(valid_values):.4f}")
                    row.append(f"{max(valid_values):.4f}")
                    #row.append(f"{sum(valid_values)/len(valid_values):.4f}")
                else:
                    row += ["---", "---", "---"]
            print(','.join(row))
            writer.writerow(row)
            f.flush()
            buffers = [[] for _ in range(16)]
    except KeyboardInterrupt:
        print("종료합니다.")
    finally:
        f.close()

# 메인 함수
def main():
    parser = argparse.ArgumentParser(description='RPi-GP40 센서값 CSV 저장')
    parser.add_argument('-r', '--range', nargs='+', help='입력 범위 설정값 (하나만 입력하면 전체 채널에 적용됨)')
    args = parser.parse_args()

    # 기본값은 0 (±10V)로 설정
    if args.range:
        if len(args.range) == 1:
            val = int(args.range[0], 16)
            for ch in range(16):  # (기존 8)
                channel_ranges[ch] = val
        elif len(args.range) == 16:  # (기존 8)
            for ch in range(16):
                channel_ranges[ch] = int(args.range[ch], 16)
        else:
            print("-r 인자는 1개 또는 16개만 허용됩니다.")
            sys.exit(1)
    else:
        channel_ranges[:] = [0] * 16  # (기존 8)

    spi.open(0, 0)
    spi.no_cs = True
    spi.mode = 1
    spi.max_speed_hz = 10000000

    init_gp40()

    for ch in range(16):  # (기존 8)
        if channel_ranges[ch] <= 9:
            set_channel_range(ch, range_registers[channel_ranges[ch]])

    log_adc_csv()

    GPIO.output(ISO_PWR_GPIO, False)
    GPIO.cleanup()

if __name__ == '__main__':
    main()
