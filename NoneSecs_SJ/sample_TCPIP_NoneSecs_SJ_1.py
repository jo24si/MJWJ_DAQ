# sample_TCPIP_NoneSecs_SJ_1.py
# (설명) GP40 로그 파일을 1초마다 읽고 TCP/IP로 채팅 메시지를 전송하는 프로그램 (수제님 설계)
# 2025-05-26 (수정됨)

import socket
import time
import os

def read_latest_log_line(log_path):
    """마지막 로그 라인을 읽어 반환합니다."""
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            if lines:
                return lines[-1].strip()
    except Exception as e:
        print(f"[오류] 로그 읽기 실패: {e}")
    return None

def send_tcp_message(ip, port, message):
    """지정된 IP와 포트로 메시지를 전송합니다."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(message.encode())
    except Exception as e:
        print(f"[오류] 전송 실패: {e}")

# === 설정 ===
LOG_FILE_PATH = "/home/pi/gp40_logs/log_latest.csv"  # 로그 파일 경로
SERVER_IP = "192.168.0.100"  # 수신 서버 IP
SERVER_PORT = 9000  # 수신 포트
INTERVAL_SECS = 1  # 전송 간격 (초)

# === 루프 시작 ===
print("[시작] 로그 전송을 시작합니다...")
prev_line = None

while True:
    latest_line = read_latest_log_line(LOG_FILE_PATH)
    if latest_line and latest_line != prev_line:
        print(f"[전송] {latest_line}")
        send_tcp_message(SERVER_IP, SERVER_PORT, latest_line)
        prev_line = latest_line
    time.sleep(INTERVAL_SECS)
