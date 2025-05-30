#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RPi-GP40를 사용한 아날로그 입력 읽기 및 CSV 저장 예제

# ✅ 변경 내용 요약
#1초마다 측정값을 메모리에 저장
#1분이 지나면 한꺼번에 CSV로 저장
#CSV 파일은 매 정시(1시간 단위)마다 새로 생성됨
#터미널에는 여전히 실시간으로 출력됨

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
channel_ranges = [0]*8

AD_CS_GPIO = 8
DOUT_GPIO = 12
DIN_GPIO = 13
ISO_PWR_GPIO = 27

spi = spidev.SpiDev()

# RPi-GP40 보드 초기 설정

def init_gp40():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(AD_CS_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ISO_PWR_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(DOUT_GPIO, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    time.sleep(0.5)

# SPI 통신

def spi_transfer(data):
    GPIO.output(AD_CS_GPIO, GPIO.LOW)
    result = spi.xfer(data)
    GPIO.output(AD_CS_GPIO, GPIO.HIGH)
    return result

# 채널 입력 범위 설정

def set_channel_range(ch, r):
    data = [((5 + ch) << 1) | 1, r, 0x00, 0x00]
    spi_transfer(data)

# ADC 값 읽기

def read_adc(ch):
    cmd = [0xC0 + (ch << 2), 0x00, 0x00, 0x00]
    spi_transfer(cmd)
    result = spi_transfer(cmd)
    value = (result[2] << 4) + (result[3] >> 4)
    return value

# 실시간 CSV 기록 함수

def log_adc_csv():
    now = datetime.now()
    last_hour = now.hour
    csv_file = now.strftime("adc_log_%Y%m%d_%H.csv")
    f = open(csv_file, 'a', newline='')
    writer = csv.writer(f)
    buffer = []
    last_flush = time.time()

    try:
        while True:
            now = datetime.now()
            # 1시간마다 새 파일 열기
            if now.hour != last_hour:
                f.close()
                csv_file = now.strftime("adc_log_%Y%m%d_%H.csv")
                f = open(csv_file, 'a', newline='')
                writer = csv.writer(f)
                last_hour = now.hour

            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            values = []
            for ch in range(8):
                if channel_ranges[ch] <= 9:
                    raw = read_adc(ch)
                    val = (raw - range_offsets[channel_ranges[ch]]) * range_scales[channel_ranges[ch]] / 1000
                    values.append(f"{val:.4f}")
                else:
                    values.append("---")
            print(timestamp, ','.join(values))
            buffer.append([timestamp] + values)

            # 1분마다 버퍼된 데이터 저장
            if time.time() - last_flush >= 60:
                writer.writerows(buffer)
                f.flush()
                buffer.clear()
                last_flush = time.time()

            time.sleep(1)
    except KeyboardInterrupt:
        print("종료합니다.")
    finally:
        if buffer:
            writer.writerows(buffer)
            f.flush()
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
            for ch in range(8):
                channel_ranges[ch] = val
        elif len(args.range) == 8:
            for ch in range(8):
                channel_ranges[ch] = int(args.range[ch], 16)
        else:
            print("-r 인자는 1개 또는 8개만 허용됩니다.")
            sys.exit(1)
    else:
        channel_ranges[:] = [0] * 8  # 기본은 모두 ±10V

    spi.open(0, 0)
    spi.no_cs = True
    spi.mode = 1
    spi.max_speed_hz = 10000000

    init_gp40()

    for ch in range(8):
        if channel_ranges[ch] <= 9:
            set_channel_range(ch, range_registers[channel_ranges[ch]])

    log_adc_csv()

    GPIO.output(ISO_PWR_GPIO, False)
    GPIO.cleanup()

if __name__ == '__main__':
    main()
