#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2020-10-23: SPI CS端子를 GPIO 제어 방식으로 변경

import sys, os
import time

import spidev  # SPI 제어용
import RPi.GPIO as GPIO  # GPIO 제어용

from datetime import datetime, timedelta

import csv
import traceback

# 전역 변수
v_rstr = ["±10V", "±5V", "±2.5V", "±1.25V", "±0.5V", "0-10V", "0-5V", "0-2.5V", "0-1.25V", "0-20mA", "없음"]  # 범위 문자열
v_chn = [0, 1, 2, 3, 11, 5, 6, 7, 15, 6, 0]  # 범위 선택 레지스터에 쓰여질 값의 테이블
v_chu = [0x800, 0x800, 0x800, 0x800, 0x800, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000]  # 실제 값 변환 감소 값 0x800: 양극성 0x000: 단극성
v_chm = [5.00, 2.50, 1.25, 0.625, 0.3125, 2.50, 1.25, 0.625, 0.3125, 5.00, 0.0]  # 실제 값 변환 곱셈 값 1LSB[mV](/[uA])
v_chr = [0, 0, 0, 0, 0, 0, 0, 0]  # ch0-7의 입력 범위 초기값
v_adach = 0  # AD 경고 발생 ch bit0-7=ch0-7 bit8=DIN
v_adadt = 0  # 디지털 입력 감지 시의 ADC ch0 값
# ADCS = 8  # AD SPI CS단자의의 GPIO 번호 8

# RPi-GP40 초기 설정
def init_GP40():
    # 브로드컴 핀 번호 사용
    GPIO.setmode(GPIO.BCM)  
    # 경고 메시지 표시 안 함
    GPIO.setwarnings(False)
    # ADCS 는 GPIO단자로 제어한다
    GPIO.setup(ADCS, GPIO.OUT, initial=GPIO.HIGH)  
    # RPi-GP40절연전원ON
    GPIO.setup(27, GPIO.OUT, initial=GPIO.HIGH)  
    # DOUT단자출력설정 LOW (=OFF: 오픈)
    GPIO.setup(DOUT, GPIO.OUT, initial=GPIO.LOW)  
    # DIN단자입력설정
    GPIO.setup(DIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)  
    # 전원 안정 대기
    time.sleep(0.5)  

# ADC와의 SPI 데이터 전송
# 2020-05-27 이후의 raspi-os에서 SPI CS 단자에 불필요한 'L' 펄스가 발생하는 현상의 대책으로 GPIO 제어 방식으로 변경 (2020-10-23)
def xfer_spiadc(wd):
    # SPI CS0='L'을 GPIO 단자로 제어한다
    GPIO.output(ADCS, 0)  
    rd = spi.xfer(wd)
    # SPI CS0='H'
    GPIO.output(ADCS, 1)  
    return rd

# 지정한 ch의 범위 선택 레지스터 값 설정
def set_adrange(ch, r):
    # ch의 입력 범위 설정
    wdat = [((5 + ch) << 1) | 1, r, 0x00, 0x00]  
    rdat = xfer_spiadc(wdat)

# 지정한 ch의 범위 선택 레지스터 값 가져오기
def get_adrange(ch):
    # ch의 입력 범위 가져오기
    wdat = [((5 + ch) << 1) | 0, 0x00, 0x00, 0x00]  
    rdat = xfer_spiadc(wdat)
    return rdat[2]

# 지정한 ch의 AD 변환 데이터 가져오기
def get_addata(ch):
    # ch'ch'를 AD 변환
    wdat = [0xc0 + (ch << 2), 0x00, 0x00, 0x00]  
    rdat = xfer_spiadc(wdat)  # ch지정
    # AD 데이터 가져오기
    rdat = xfer_spiadc(wdat)  
    # AD 변환 값
    adat = (rdat[2] << 4) + (rdat[3] >> 4)  
    return adat

# ch0-7의 AD 변환 실행 및 결과 표시
def print_adc(v_intv):  # intv: 표시 간격[sec] 
    global adach
    v_array = []
    while True:
        v_adat = []; v_volt = [];
        for adc in range(8):  # ch0-7
            if (v_chr[adc] > 9):  # 무효 ch라면,
                # AD 변환 없음
                print("%8s ch%d:        [---]" % (v_rstr[v_chr[adc]], adc))  
            else:  # 유효 ch라면,
                # ch'adc'를 AD 변환
                adat = get_addata(adc)  
                # 입력 범위에서의 실제 값 계산 = (AD 변환 값-감소 값)x 곱셈 값
                volt = (adat - v_chu[v_chr[adc]]) * v_chm[v_chr[adc]]
                v_adat.append(adat)
                v_volt.append(volt)
        print(f'[{datetime.now()}] {[f"{x:.1f}" for x in v_volt]}(mV), ADAT : {v_adat}')
        v_array.append([datetime.now()] + v_volt)

        if len(v_array) > 30:
            # csv 파일 작성
            with open(os.path.join(v_abs_path, f"{datetime.now().strftime('%Y%m%d_%H0000')}_adc.csv"), "a+") as wf:
                csv.writer(wf).writerows(v_array)
            v_array = []  # init

        # 간격으로 시간 지연
        time.sleep(v_intv)

    print("")

##########################################################################################################################################

v_abs_path = r'/home/pi/Documents/spiadc'

def get_arg(index):
    try:
        sys.argv[index]
    except IndexError:
        return ''
    else:
        return sys.argv[index]

# main
if __name__ == "__main__":
    global ADCS  # 8 : (CH01~08), 7 : (CH09~16)
    if get_arg(1) == '' or int(get_arg(1)): ADCS = 8
    else: ADCS = 7

    try:
        v_chr = [1] * 8
        v_interval = 0.1

        # RaspberryPi SPI 기능 설정
        spi = spidev.SpiDev()  # RPi-GP40는 SPI를 사용
        spi.open(0, 0)  #SPI0, CEN0으로 오픈
        spi.no_cs = True  #CS는 spidev가 아니라 GPIO로 제어함 (Ra)
        spi.mode = 1  #SPI 클럭 설정: CPOL=0(정논리), CPHA=1(H→L로 데이터 수집)
        spi.max_speed_hz = 10000000  #SPI 클럭 최대 주파수: 17MHz로 설정
        #단, 2018년 4월 기준 커널 사양에서는 설정값보다 실제 주파수가 낮아짐
        #17MHz → 10.5MHz
        #10MHz → 6.2MHz
        #8MHz → 5MHz
        #28MHz → 15.6MHz    
        DOUT = 12  #디지털 출력: GPIO12(JP8: 기본값) / GPIO14(JP7)
        DIN = 13  #디지털 입력: GPIO13(JP6: 기본값) / GPIO15(JP5)
  
        # RPi-GP40 초기 설정
        init_GP40()

        # 입력 범위 설정
        for adc in range(8):
            if (v_chr[adc] <= 9):  # 유효 ch라면,
                # ch'c'의 입력 범위 설정
                set_adrange(adc, v_chn[v_chr[adc]])  

        # 인자에 의한 직접 실행 형식
        print_adc(v_interval)  # interval 간격으로 AD 변환 값 표시
        raise GTE

    except GTE:
        pass
    # 예외 처리
    except KeyboardInterrupt:  # CTRL-C 키가 눌러졌을 때,
        print("Keyboard Interrupt !!")  # 중단
    except Exception as ex:  # 기타 예외 발생 시
        print('에러 발생[__main__] : {0}\n{1}'.format(ex, ''.join(traceback.TracebackException.from_exception(ex).format())));

    finally:
        # RPi-GP40의 절연전원OFF
        GPIO.output(27, False)  
        GPIO.cleanup()
        sys.exit()