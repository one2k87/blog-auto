#!/usr/bin/env bash
# 매일 실행용 래퍼. cron 에서 이 파일을 호출하면 됨.
cd "$(dirname "$0")"
# 가상환경을 쓴다면 아래 주석 해제
# source venv/bin/activate
python3 main.py >> run.log 2>&1
