
from datetime import datetime

# FTP 접속 정보
FTP_HOST = "서버주소"
FTP_USER = "아이디"
FTP_PASS = "비밀번호"

# 디렉토리 경로
REMOTE_DIR = "/server/path"
LOCAL_DIR = "/home/pi/logs"            # CSV 파일 저장 경로
LOG_DIR = "/home/pi/logs/logs"         # 로그 파일 저장 경로

# 로그 파일 이름 생성 함수
def get_log_filename(date: datetime = None):
    if date is None:
        date = datetime.now()
    return f"adc_log_{date.strftime('%Y%m%d')}.csv"
