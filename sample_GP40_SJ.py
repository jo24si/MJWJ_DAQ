#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RPi-GP40를 사용한 샘플링 속도 측정 예제

import sys
import time
import argparse
import spidev
import RPi.GPIO as GPIO
from datetime import datetime

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

# 초기 설정

def init_gp40():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(AD_CS_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ISO_PWR_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(DOUT_GPIO, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    time.sleep(0.5)

# SPI 전송

def spi_transfer(data):
    GPIO.output(AD_CS_GPIO, GPIO.LOW)
    result = spi.xfer(data)
    GPIO.output(AD_CS_GPIO, GPIO.HIGH)
    return result

# 채널 범위 설정

def set_channel_range(ch, r):
    data = [((5 + ch) << 1) | 1, r, 0x00, 0x00]
    spi_transfer(data)

# ADC 데이터 읽기

def read_adc(ch):
    cmd = [0xC0 + (ch << 2), 0x00, 0x00, 0x00]
    spi_transfer(cmd)
    result = spi_transfer(cmd)
    value = (result[2] << 4) + (result[3] >> 4)
    return value

# 최대 샘플링 속도 측정 함수

def measure_sampling_rate(duration_sec=5):
    print(f"{duration_sec}초 동안 8채널 전체를 몇 번 읽을 수 있는지 측정합니다...")
    count = 0
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        for ch in range(8):
            read_adc(ch)
        count += 1
    elapsed = time.time() - start_time
    print(f"총 반복 횟수: {count}회 (8채널 = {count * 8}회 측정)")
    print(f"평균 속도: {count / elapsed:.2f} Hz (1초당 전체 루프 횟수)")
    print(f"한 채널 기준 약 {(count * 8) / elapsed:.2f} 샘플/초")

# 메인 함수

def main():
    parser = argparse.ArgumentParser(description='RPi-GP40 샘플링 속도 테스트')
    parser.add_argument('-r', '--range', nargs=8, help='입력 범위 설정값 0~9  예: -r 0 0 0 0 0 0 0 0')
    args = parser.parse_args()

    if args.range:
        for ch in range(8):
            channel_ranges[ch] = int(args.range[ch], 16)

    spi.open(0, 0)
    spi.no_cs = True
    spi.mode = 1
    spi.max_speed_hz = 10000000

    init_gp40()

    for ch in range(8):
        if channel_ranges[ch] <= 9:
            set_channel_range(ch, range_registers[channel_ranges[ch]])

    measure_sampling_rate()

    GPIO.output(ISO_PWR_GPIO, False)
    GPIO.cleanup()

if __name__ == '__main__':
    main()
