# sample_TCPIP_NoneSecs_SJ_1.1.py
# (설명) GP40 로그 파일을 1초마다 읽고 TCP/IP로 클라이언트에게 전송하는 서버 프로그램 (수제님 설계)
# 버전 1.1 / 2025-05-28
# v0.1: 기본 TCP 서버 구조 생성
# v0.2: 로그 읽기 함수 추가 및 경로 설정 반영
# v0.3: 클라이언트 종료 시 서버 루프 지속되도록 수정
# v0.4: 로그 변경이 없을 경우 마지막 줄 반복 전송 기능 추가
# v0.5: 로그 파일 내용이 같아도 파일 갱신되면 다시 전송되도록 수정
# v0.6: 파일 변경 없어도 1초마다 무조건 전송하도록 복구 + mtime 체크 병행 유지
# v0.7: 파일 수정시간 체크 기반으로 로그 줄을 읽되, 매초 무조건 전송 유지
# v0.8: 프로그램 종료 시 포트 점유 해제 및 종료 메시지 출력 추가
# v0.9: "수제메롱" 포함 최신 텍스트 파일 자동 탐색 및 매초 루프 유지하도록 수정
# v1.0: 종료 시 포트 반환 보장을 위한 try/finally 구조 도입 및 종료 시 KeyboardInterrupt 명확히 처리 / 주석 정리 + 설정값 정렬
# v1.1: NONSECS 형식 포맷 전송 기능 추가, 16CH 데이터를 키-값으로 구성하여 메시지 포맷 가공
# v1.2: ini 없을시 자동생성 기능 추가 _160616 수제

import socket
# 소켓 통신 모듈을 불러옵니다

import time
# 시간 관련 함수 사용을 위해 임포트합니다

import os
import signal
import sys
import configparser


# ▼ [INI 없으면 만들기]
def create_default_none_secs_ini(filename='NoneSecsConfig_SJ.ini'):
    config = configparser.ConfigParser()
    config.optionxform = str

    config['GENERAL'] = {
        'SEARCH_KEYWORD': '수제메롱',
        'SEARCH_DIR': '/home/pi/gp40_logs',
        'FILENAME_EXTENSIONS': '.csv,.txt,.log'
    }

    config['DEVICE'] = {
        'EQPID': 'A2ELA59A_CLNU_OZ01_NS02',
        'TRID': '3'
    }

    config['SENSOR'] = {f'SVID_{i}': f'{10000+i}' for i in range(1, 17)}

    config['SERVER'] = {
        'LISTEN_IP': '0.0.0.0',
        'LISTEN_PORT': '9000'
    }

    with open(filename, 'w') as f:
        config.write(f)

    print(f'[자동생성] 설정 파일 생성 완료: {filename}')


# ▼ [INI 설정 불러오기 블럭 시작]
if not os.path.exists('NoneSecsConfig_SJ.ini'):
    print('[경고] 설정 파일이 없어 기본값으로 생성합니다.')
    create_default_none_secs_ini()
config = configparser.ConfigParser()
config.optionxform = str
config.read('NoneSecsConfig_SJ.ini')

SEARCH_KEYWORD = config['GENERAL']['SEARCH_KEYWORD']
SEARCH_DIR     = config['GENERAL']['SEARCH_DIR']
FILENAME_EXTENSIONS = config['GENERAL']['FILENAME_EXTENSIONS'].split(',')

EQPID = config['DEVICE']['EQPID']
TRID = int(config['DEVICE']['TRID'])

SVID_1 = int(config['SENSOR']['SVID_1'])
SVID_2 = int(config['SENSOR']['SVID_2'])
SVID_3 = int(config['SENSOR']['SVID_3'])
SVID_4 = int(config['SENSOR']['SVID_4'])
SVID_5 = int(config['SENSOR']['SVID_5'])
SVID_6 = int(config['SENSOR']['SVID_6'])
SVID_7 = int(config['SENSOR']['SVID_7'])
SVID_8 = int(config['SENSOR']['SVID_8'])
SVID_9 = int(config['SENSOR']['SVID_9'])
SVID_10 = int(config['SENSOR']['SVID_10'])
SVID_11 = int(config['SENSOR']['SVID_11'])
SVID_12 = int(config['SENSOR']['SVID_12'])
SVID_13 = int(config['SENSOR']['SVID_13'])
SVID_14 = int(config['SENSOR']['SVID_14'])
SVID_15 = int(config['SENSOR']['SVID_15'])
SVID_16 = int(config['SENSOR']['SVID_16'])

LISTEN_IP = config['SERVER']['LISTEN_IP']
LISTEN_PORT = int(config['SERVER']['LISTEN_PORT'])
# ▲ [INI 설정 불러오기 블럭 끝]

"""
TEXT_EXTENSIONS = [".csv", ".txt", ".log"]  # 탐색 대상 파일 확장자 목록
KEYWORD = "수제메롱"  # 특정 키워드가 파일명에 포함돼야 유효 로그로 인식
SEARCH_DIR = "/home/pi/gp40_logs"  # 로그 파일들이 저장된 디렉터리 경로


# (추가됨) 전역 변수: 장비ID, 이송번호, 센서 SVID
EQPID = "A2ELA59A_CLNU_OZ01_NS02"
TRID = 3

SVID_1 = 10001
SVID_2 = 10002
SVID_3 = 10003
SVID_4 = 10004
SVID_5 = 10005
SVID_6 = 10006
SVID_7 = 10007
SVID_8 = 10008
SVID_9 = 10009
SVID_10 = 10010
SVID_11 = 10011
SVID_12 = 10012
SVID_13 = 10013
SVID_14 = 10014
SVID_15 = 10015
SVID_16 = 10016
# === 설정 ===
LISTEN_IP = "0.0.0.0"  # 서버가 수신할 IP (모든 인터페이스)
LISTEN_PORT = 9000     # 서버가 수신할 포트
"""


# 로그 한 줄을 포맷 문자열로 변환하는 함수
def convert_log_to_tooldata_format(log_line):
    try:
        parts = log_line.strip().split(',')  # 쉼표 기준으로 데이터 나누기
        if len(parts) < 17:
            return "[오류] 센서 값 부족"

        timestamp = parts[0].replace('_', ' ').replace('-', '/')  # 날짜 형식 변환
        sensor_values = parts[1:17]  # 센서 값 16개 추출
        svid_list = [SVID_1, SVID_2, SVID_3, SVID_4, SVID_5, SVID_6, SVID_7, SVID_8,
                     SVID_9, SVID_10, SVID_11, SVID_12, SVID_13, SVID_14, SVID_15, SVID_16]

        sensor_str = "^".join([f"{svid}={val}" for svid, val in zip(svid_list, sensor_values)])  # 센서값 문자열 결합

        formatted = (
            "NONSECS_TOOLDATA HDR=(null,null,null) "
            f"TIME_STAMP={timestamp} "
            f"EQPID={EQPID} TRID={TRID} LOTID=(NULL) RECPID=(NULL) "
            f"SENSOR_VALUES={{" + sensor_str + "}}"
        )
        return formatted

    except Exception as e:
        return f"[오류] 변환 실패: {e}"

# 가장 최근의 로그 파일 경로 찾기 함수
def find_latest_log_file(search_dir):
    """지정된 디렉토리에서 '수제메롱'이 포함된 최신 텍스트 파일 경로 반환"""
    latest_file = None
    latest_mtime = 0
    for root, _, files in os.walk(search_dir):  # 디렉터리 전체 탐색
        for fname in files:
            if SEARCH_KEYWORD in fname and os.path.splitext(fname)[1].lower() in FILENAME_EXTENSIONS:
                full_path = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(full_path)
                    if mtime > latest_mtime:
                        latest_file = full_path  # 가장 최근에 수정된 파일로 갱신
                        latest_mtime = mtime
                except:
                    continue
    return latest_file

# 로그 파일의 마지막 줄을 읽고 새 내용일 경우만 반환
def read_latest_log_line(log_path, last_mtime):
    try:
        if log_path and os.path.exists(log_path):
            mtime = os.path.getmtime(log_path)
            if mtime != last_mtime:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        return lines[-1].strip(), mtime
            else:
                return None, last_mtime
    except Exception as e:
        print(f"[오류] 로그 읽기 실패: {e}")
    return None, last_mtime

# 시스템 종료 신호가 들어왔을 때 안전하게 종료하기 위한 함수
# 종료 시그널 처리 핸들러: 포트 점유 해제 및 메시지 출력

def graceful_exit(signum, frame):
    print("\n[종료] 서버가 정상적으로 종료되었습니다.")
    sys.exit(0)

# SIGINT (Ctrl+C) 및 SIGTERM (시스템 종료요청) 모두 graceful 처리
signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# TCP 서버 구동 함수
def start_tcp_server(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 포트 재사용 설정
        server_socket.bind((ip, port))  # IP, 포트 바인딩
        server_socket.listen()  # 클라이언트 연결 대기
        print(f"[서버] 수신 대기 중: {ip}:{port}")

        while True:
            client_socket, addr = server_socket.accept()  # 클라이언트 접속 수락
            print(f"[접속] 클라이언트: {addr}")
            prev_line = None
            last_mtime = 0
            log_path = find_latest_log_file(SEARCH_DIR)  # 첫 로그 파일 지정
            try:
                with client_socket:
                    while True:
                        log_path = find_latest_log_file(SEARCH_DIR)  # 반복적으로 최신 로그 탐색
                        latest_line, last_mtime = read_latest_log_line(log_path, last_mtime)
                        if latest_line:
                            if latest_line != prev_line:
                                prev_line = latest_line
                                print(f"[전송:갱신] {latest_line}")
                            else:
                                print(f"[전송:반복] {latest_line}")
                        else:
                            print("[대기중] 로그 없음 또는 미갱신")

                        if prev_line:
                            try:
                                # 센서 포맷 변환 후 전송
                                converted_line = convert_log_to_tooldata_format(prev_line)
                                client_socket.sendall((converted_line + "\n").encode())  # 문자열 전송
                            except Exception as e:
                                print(f"[전송 실패] {e}")
                                break
                        time.sleep(1)
            except Exception as e:
                print(f"[연결 종료] {addr} / 이유: {e}")
                continue

# === 서버 시작 ===
print("[시작] TCP 수신 서버 실행 중...")
start_tcp_server(LISTEN_IP, LISTEN_PORT)
