# sample_TCPIP_NoneSecs_SJ_1.py
# (설명) GP40 로그 파일을 1초마다 읽고 TCP/IP로 클라이언트에게 전송하는 서버 프로그램 (수제님 설계)
# 버전 1.0 / 2025-05-26
# v0.1: 기본 TCP 서버 구조 생성
# v0.2: 로그 읽기 함수 추가 및 경로 설정 반영
# v0.3: 클라이언트 종료 시 서버 루프 지속되도록 수정
# v0.4: 로그 변경이 없을 경우 마지막 줄 반복 전송 기능 추가
# v0.5: 로그 파일 내용이 같아도 파일 갱신되면 다시 전송되도록 수정
# v0.6: 파일 변경 없어도 1초마다 무조건 전송하도록 복구 + mtime 체크 병행 유지
# v0.7: 파일 수정시간 체크 기반으로 로그 줄을 읽되, 매초 무조건 전송 유지
# v0.8: 프로그램 종료 시 포트 점유 해제 및 종료 메시지 출력 추가
# v0.9: "수제메롱" 포함 최신 텍스트 파일 자동 탐색 및 매초 루프 유지하도록 수정
# v1.0: 종료 시 포트 반환 보장을 위한 try/finally 구조 도입 및 로그 출력 추가

import socket
import time
import os
import signal
import sys

# 허용되는 텍스트 파일 확장자
TEXT_EXTENSIONS = [".csv", ".txt", ".log"]

# 로그 파일 이름에 포함되어야 할 키워드
KEYWORD = "adc_log_2"

# 로그 파일을 찾을 기본 디렉터리
SEARCH_DIR = "/home/pi/sooje_practice"

# 가장 최근에 수정된 텍스트 로그 파일 찾기
def find_latest_log_file(search_dir):
    latest_file = None
    latest_mtime = 0
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if KEYWORD in fname and os.path.splitext(fname)[1].lower() in TEXT_EXTENSIONS:
                full_path = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(full_path)
                    if mtime > latest_mtime:
                        latest_file = full_path
                        latest_mtime = mtime
                except:
                    continue
    return latest_file

# 로그 파일의 마지막 줄을 읽는 함수 (수정된 경우에만)
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

# 종료 시 메시지를 출력하고 안전하게 종료
def graceful_exit(signum, frame):
    print("\n[종료] 서버가 정상적으로 종료되었습니다.")
    sys.exit(0)

# 종료 시그널 등록
signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# TCP 서버 메인 함수
def start_tcp_server(ip, port):
    # 소켓 생성 및 재사용 설정
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((ip, port))
        server_socket.listen()
        print(f"[서버] 수신 대기 중: {ip}:{port}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"[접속] 클라이언트: {addr}")
            prev_line = None
            last_mtime = 0
            log_path = find_latest_log_file(SEARCH_DIR)

            try:
                with client_socket:
                    while True:
                        # 매 루프마다 가장 최신 로그 파일 재탐색
                        log_path = find_latest_log_file(SEARCH_DIR)
                        latest_line, last_mtime = read_latest_log_line(log_path, last_mtime)

                        if latest_line:
                            if latest_line != prev_line:
                                prev_line = latest_line
                                print(f"[전송:갱신] {latest_line}")
                            else:
                                print(f"[전송:반복] {latest_line}")
                        else:
                            print("[대기중] 로그 없음 또는 미갱신")

                        # 이전 줄이라도 항상 전송 시도
                        if prev_line:
                            try:
                                client_socket.sendall((prev_line + "\n").encode())
                            except Exception as e:
                                print(f"[전송 실패] {e}")
                                break

                        time.sleep(1)
            except Exception as e:
                print(f"[연결 종료] {addr} / 이유: {e}")
                continue
    finally:
        server_socket.close()
        print("[종료] 서버 소켓이 닫혔습니다. 포트 반환 완료.")

# 서버 IP 및 포트 설정
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 9000

# 서버 실행 시작
print("[시작] TCP 수신 서버 실행 중...")
start_tcp_server(LISTEN_IP, LISTEN_PORT)
