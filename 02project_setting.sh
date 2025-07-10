#!/bin/bash
set -e

# 1. 현재 디렉토리 기준 prototype 경로를 환경 변수로 등록
export RASPA_GUI="$(pwd)/prototype"

# 1-1. ~/.bashrc에 RASPA_GUI 등록 및 즉시 적용
grep -qxF "export RASPA_GUI=\"$RASPA_GUI\"" ~/.bashrc || \
  echo "export RASPA_GUI=\"$RASPA_GUI\"" >> ~/.bashrc
source ~/.bashrc

# 2. conda 가상환경 생성
conda create -y -n raspagui python=3.9

# 3. 가상환경 활성화
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate raspagui

# 3-1. 프로젝트 디렉토리로 이동
cd "$RASPA_GUI"

# 4. requirements 설치
pip install -r requirements.txt

# 5. 서버 실행 테스트 (백그라운드로 실행)
python manage.py runserver &

# 서버 동작 확인
sleep 5
curl -s --head http://127.0.0.1:8000 | grep "200 OK" \
  && echo "✅ 서버 실행 확인됨: http://127.0.0.1:8000" \
  || echo "⚠️ 서버 실행 실패"

# 백그라운드 실행된 서버 종료
pkill -f "manage.py runserver"
