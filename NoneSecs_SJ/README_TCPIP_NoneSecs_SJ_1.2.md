
## 📡 sample_TCPIP_NoneSecs_SJ_1.2

### 개요
GP40 장비에서 생성된 로그 파일을 주기적으로 확인하고, 최신 센서 데이터를 TCP/IP 프로토콜로 실시간 전송하는 서버 프로그램입니다. 전송 형식은 `NONSECS_TOOLDATA` 포맷이며, 16채널 센서값을 포함합니다.

---

### 🔧 구성 파일

| 파일명 | 설명 |
|--------|------|
| `sample_TCPIP_NoneSecs_SJ_1.2.py` | 메인 서버 실행 코드 |
| `NoneSecsConfig_SJ.ini` | 설정파일: 경로, 키워드, IP/PORT, SVID 등 포함 |
| `gp40_logs/*.csv` | 센서 로그 파일 ("찾고 싶은 키워드" 키워드 포함 필요) |

---

### ⚙️ 주요 기능

- INI 파일로 경로/포트/SVID 자동 설정
- 최신 로그 파일 자동 탐색 및 마지막 줄 추출
- `NONSECS_TOOLDATA` 포맷으로 데이터 가공 후 전송
- 로그 변경 없을 시 이전 데이터 재전송
- 1초 간격 데이터 전송 유지
- 종료 시 Ctrl+C 또는 SIGTERM 처리로 포트 반환 보장

---

### ✅ 전송 포맷 예시

```
NONSECS_TOOLDATA HDR=(null,null,null) TIME_STAMP=2025/06/10 12:00:00 EQPID=A1AAA11A_BBBB_CC01_NS02 TRID=3 LOTID=(NULL) RECPID=(NULL) SENSOR_VALUES={10001=0.12^10002=0.34^...}
```

---

### 🧾 필요 환경

- Python 3.x
- 모듈: socket, time, os, signal, sys, configparser (표준 내장)

---

### 🚀 실행 방법

```bash
python3 sample_TCPIP_NoneSecs_SJ_1.2.py
```

> ⚠️ `NoneSecsConfig_SJ.ini` 파일과 로그 디렉토리는 같은 경로 또는 설정된 경로에 준비되어 있어야 합니다.

---

### 🚩 종료 방법

- `Ctrl+C` 또는 SIGTERM 수신 시
- 안전히 포트 해제 및 종료 메시지 출력
