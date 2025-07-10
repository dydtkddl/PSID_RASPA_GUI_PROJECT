#!/bin/bash
set -e

# conda 환경 활성화
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate raspagui

# RASPA_GUI 디렉토리로 이동
cd "$RASPA_GUI"

# 서버 실행
python manage.py runserver
