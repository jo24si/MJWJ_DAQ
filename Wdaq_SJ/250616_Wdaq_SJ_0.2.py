#ver0.4 RPi-GP40를 사용한 아날로그 입력 읽기 및 CSV 저장 예제 (2보드 확장 버전)
#ver0.5 IO 출력 입력 기능 추가 _ 조수제 250611
#ver0.6 Config기능 추가 _ 조수제 250611

import sys
import time
import argparse
import spidev
import RPi.GPIO as GPIO
import os
import csv
import configparser  # (추가) ini 파일 읽기용
from datetime import datetime

# 전압/전류 입력 범위에 대한 설정 테이블
range_names = ["±10V", "±5V", "±2.5V", "±1.25V", "±0.5V", "0-10V", "0-5V", "0-2.5V", "0-1.25V", "0-20mA", "NONE"]
range_registers = [0, 1, 2, 3, 11, 5, 6, 7, 15, 6, 0]
range_offsets = [0x800]*5 + [0x000]*5 + [0x000]
range_scales = [5.00, 2.50, 1.25, 0.625, 0.3125,
                 2.50, 1.25, 0.625, 0.3125, 5.00, 0.0]
# channel_ranges = [0]*8  # (기존)
channel_ranges = [0]*16  # 16채널 대응

# GPIO 설정 (ini에서 제거, 한정 값으로 관리)
AD_CS_GPIO_1 = 8  # 보드1
AD_CS_GPIO_2 = 7  # 보드2
DOUT_GPIO = 12
DIN_GPIO = 13
ISO_PWR_GPIO = 27
INPUT_GPIO_PINS = [5, 17, 27, 22]  # 입력 핀
OUTPUT_GPIO_PINS = [23, 24]        # 출력 핀

# ▼ [INI 없으면 만들기]
def create_default_ini(filename='WdaqConfig_SJ.ini'):
    config = configparser.ConfigParser()
    config.optionxform = str
    config['log'] = {
        'dir': './DAQ_LOG',
        'days': '30'
    }
    config['acquisition'] = {
        'sampling_rate': '1000'
    }
    config['channel_range'] = {f'ch{ch}': '0' for ch in range(16)}
    with open(filename, 'w') as configfile:
        config.write(configfile)
    print(f'[자동생성] 기본 설정 파일 생성 완료: {filename}')


# ▼ [INI 설정 불러오기]
if not os.path.exists('WdaqConfig_SJ.ini'):
    print('[경고] 설정 파일이 없어 기본 설정으로 자동 생성합니다.')
    create_default_ini()

config = configparser.ConfigParser()
config.optionxform = str  # 키 대소문자 구분 유지
config.read('WdaqConfig_SJ.ini')

LOG_LIFE_DAYS = int(config['log']['days'])
log_dir = config['log']['dir']
os.makedirs(log_dir, exist_ok=True)

SAMPLING_RATE = int(config['acquisition']['sampling_rate'])
SAMPLE_INTERVAL = 1.0 / SAMPLING_RATE

for ch in range(16):
    channel_ranges[ch] = int(config['channel_range'][f'ch{ch}'])

spi = spidev.SpiDev()

# RPi-GP40 보드 초기 설정
# (아날로그 입력부)
def init_gp40():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(AD_CS_GPIO_1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(AD_CS_GPIO_2, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ISO_PWR_GPIO, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(DOUT_GPIO, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
#(IO 입력부)
    for pin in INPUT_GPIO_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    for pin in OUTPUT_GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(0.5)

# 보드 선택 함수 (추가)
def select_adc_board(ch):
    if ch < 8:
        GPIO.output(AD_CS_GPIO_1, GPIO.LOW)
        GPIO.output(AD_CS_GPIO_2, GPIO.HIGH)
        return ch
    else:
        GPIO.output(AD_CS_GPIO_1, GPIO.HIGH)
        GPIO.output(AD_CS_GPIO_2, GPIO.LOW)
        return ch - 8

# SPI 통신 (CS 핀 직접 지정 방식으로 수정됨)
def spi_transfer(data, cs_gpio):
    GPIO.output(cs_gpio, GPIO.LOW)
    result = spi.xfer(data)
    GPIO.output(cs_gpio, GPIO.HIGH)
    return result

# 채널 입력 범위 설정
# (기존)
def set_channel_range(ch, r):
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

# 매일 00시 CSV파일 삭제 (메모리에 30일간 log만 저장하고 초과한 것을 삭제) 250616_수제
def clean_old_logs(log_dir, days):
    cutoff = time.time() - (days * 86400)
    for fname in os.listdir(log_dir):
        fpath = os.path.join(log_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(".csv"):
            if os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                print(f"[삭제됨] {fname}")

# 실시간 CSV 기록 함수 (1000Hz 측정 → 1초마다 min/max/avg 저장)
def log_adc_csv():
    now = datetime.now()
    last_hour = now.hour
    csv_file = os.path.join(log_dir, now.strftime("DAQ_LOG_%Y%m%d_%H%M%S.csv"))
    f = open(csv_file, 'a', newline='')
    writer = csv.writer(f)

    buffers = [[] for _ in range(16)]
    start_time = time.perf_counter()

    try:
        while True:
            now = datetime.now()

            # 자정에 log삭제 실행 (1달치 보존)
            if now.hour == 0 and now.minute == 0 and now.second < 2:
                clean_old_logs(log_dir, days=LOG_LIFE_DAYS)
            #매시 정각마다 새 파일로 만들기
            if now.hour != last_hour:
                f.close()
                csv_file = os.path.join(log_dir,now.strftime("DAQ_LOG_%Y%m%d_%H%M%S.csv"))
                f = open(csv_file, 'a', newline='')
                writer = csv.writer(f)
                last_hour = now.hour

            # 기준 시간 기록 (현재 시점의 고해상도 타이머)
            t0 = time.perf_counter()

            # 약 1초 동안 반복 수행 (실제 loop duration ≈ 1초)
            while time.perf_counter() - t0 < 1.0:
                # 16채널에 대해 순차적으로 읽음
                # 각 채널 설정값이 0~9 (유효 범위)이면 ADC 측정
                # 그 외 (10번 = NONE)은 측정 생략하고 None 기록
                for ch in range(16):
                    if channel_ranges[ch] <= 9:
                        raw = read_adc(ch)

                        # 정규화된 실측값 계산
                        # (raw 값에서 오프셋을 빼고, 설정된 스케일로 환산 → 단위: V 또는 mA)
                        val = (raw - range_offsets[channel_ranges[ch]]) * range_scales[channel_ranges[ch]] / 1000

                        # 해당 채널 버퍼에 저장 (나중에 min/max/avg 계산용)
                        buffers[ch].append(val)
                    else:
                        # 설정이 없는 채널은 None으로 버퍼에 기록
                        buffers[ch].append(None)
                time.sleep(0.001)  # 샘플 간 간격 1ms → 약 1000Hz 수집 목표


            # 현재 시각을 "년-월-일_시:분:초.밀리초" 형식의 문자열로 생성
            # 예: "2025-06-16_00:00:01.123"
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")[:-3]

            # 디지털 입력 핀들(GPIO 5,17,27,22 등)의 상태를 모두 읽어서 리스트로 저장 HIGH → 1, LOW → 0
            input_vals = [GPIO.input(pin) for pin in INPUT_GPIO_PINS]
            row = [timestamp] + input_vals

            for ch_buf in buffers:
                # None이 아닌 실측값만 필터링 → 유효한 값만 남김
                valid_values = [v for v in ch_buf if v is not None]
                
                if valid_values:        # 유효한 값이 있는 경우 → 소수점 4자리까지 포맷팅하여 CSV에 추가
                    #row.append(f"{min(valid_values):.4f}")
                    row.append(f"{max(valid_values):.4f}")
                    #row.append(f"{sum(valid_values)/len(valid_values):.4f}")

                else:                    # 해당 채널에 수집된 값이 없다면 빈 값으로 대체
                    row += ["---", "---", "---"]

            # 출력 제어 로직 (현재 주석처리)
            # if GPIO.input(5):  # INPUT1 기반 제어
            #     GPIO.output(23, GPIO.HIGH)  # OUTPUT1 ON
            # else:
            #     GPIO.output(23, GPIO.LOW)   # OUTPUT1 OFF
            #
            # ch0_values = buffers[0]  # ADC CH0 평균 기반 제어
            # if ch0_values:
            #     avg = sum(ch0_values) / len(ch0_values)
            #     if avg > 0.5:
            #         GPIO.output(24, GPIO.HIGH)  # OUTPUT2 ON
            #     else:
            #         GPIO.output(24, GPIO.LOW)   # OUTPUT2 OFF

            print(','.join(str(x) for x in row))
            writer.writerow(row)
            f.flush()
            # buffers = [[] for _ in range(8)]  # (기존)
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
            for ch in range(16):
                channel_ranges[ch] = val
        elif len(args.range) == 16:
            for ch in range(16):
                channel_ranges[ch] = int(args.range[ch], 16)
        else:
            print("-r 인자는 1개 또는 16개만 허용됩니다.")
            sys.exit(1)
    else:
        channel_ranges[:] = [0] * 16
    # SPI 설정
    spi.open(0, 0)  # SPI 버스 0, 디바이스 0 사용 (보통 /dev/spidev0.0)
    spi.no_cs = True  # CS 핀을 자동으로 제어하지 않음 (GPIO 수동 제어 방식과 충돌 방지)
    spi.mode = 1      # SPI 모드 1 (CPOL=0, CPHA=1) — GP40 보드와 통신 조건에 맞춤
    spi.max_speed_hz = 10000000  # 최대 속도 10MHz — GP40 ADC와 안정적 통신을 위한 설정

    init_gp40()

    for ch in range(16):
        if channel_ranges[ch] <= 9:
            set_channel_range(ch, range_registers[channel_ranges[ch]])

    log_adc_csv()

    GPIO.output(ISO_PWR_GPIO, False)
    GPIO.cleanup()

if __name__ == '__main__':
    main()
