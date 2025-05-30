
import os
import time
from datetime import datetime, timedelta
from ftplib import FTP
import config  # config.py에서 설정 불러오기

current_log_date = None
log_file = None

os.makedirs(config.LOG_DIR, exist_ok=True)

def log(msg):
    global current_log_date, log_file
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    timestamp = now.strftime("[%Y-%m-%d %H:%M:%S]")

    if current_log_date != date_str:
        if log_file:
            log_file.close()
        log_filename = config.get_log_filename(now)
        log_path = os.path.join(config.LOG_DIR, log_filename)
        log_file = open(log_path, 'a')
        current_log_date = date_str

    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    log_file.write(full_msg + '\n')
    log_file.flush()

def upload_csv():
    target_time = datetime.now() - timedelta(hours=1)
    filename = f"adc_log_{target_time.strftime('%Y%m%d_%H')}.csv"
    local_path = os.path.join(config.LOCAL_DIR, filename)

    if not os.path.exists(local_path):
        log(f"[스킵] 파일 없음: {filename}")
        return

    try:
        with FTP(config.FTP_HOST) as ftp:
            ftp.login(config.FTP_USER, config.FTP_PASS)
            ftp.cwd(config.REMOTE_DIR)

            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f)

            log(f"[업로드 완료] {filename}")
    except Exception as e:
        log(f"[에러] FTP 업로드 실패: {e}")

def main_loop():
    while True:
        now = datetime.now()
        next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        log(f"다음 전송까지 {int(wait_seconds)}초 대기 (예정 시각: {next_run.strftime('%H:%M:%S')})")
        time.sleep(wait_seconds)
        upload_csv()

if __name__ == '__main__':
    log("CSV 자동 업로드 시작")
    main_loop()
