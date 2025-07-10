#!/bin/bash

# bashrc 없으면 생성
[ -f ~/.bashrc ] || touch ~/.bashrc

# 현재 경로를 RASPA_GUI로 환경변수 지정
export RASPA_GUI=${PWD}
grep -qxF "export RASPA_GUI=${PWD}" ~/.bashrc || echo "export RASPA_GUI=${PWD}" >> ~/.bashrc

# .bashrc 적용
source ~/.bashrc

# Anaconda 미설치 시 다운로드 및 설치
if ! command -v conda &> /dev/null; then
  wget https://repo.anaconda.com/archive/Anaconda3-2023.09-0-Linux-x86_64.sh
  bash Anaconda3-2023.09-0-Linux-x86_64.sh -b -p $HOME/anaconda3
  export PATH="$HOME/anaconda3/bin:$PATH"
  grep -qxF 'export PATH="$HOME/anaconda3/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/anaconda3/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
fi

# Conda 버전 확인
conda --version

# raspagui 환경 없으면 생성
if ! conda info --envs | grep -q raspagui; then
  conda create -y -n raspagui python=3.9
fi

# 환경 활성화
source ~/.bashrc
conda activate raspagui

# requirements.txt 설치
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# Windows C드라이브에 run_raspagui.bat 생성
cat <<EOF > /mnt/c/run_raspagui.bat
@echo off
REM WSL에서 django 서버 실행
set WSL_PROJECT_PATH=${RASPA_GUI}
wsl bash -ic "cd ${RASPA_GUI} && source ~/.bashrc && conda activate raspagui && python manage.py runserver 0.0.0.0:8000"
timeout /t 2 >nul
start http://127.0.0.1:8000
EOF

echo "======================================"
echo "/mnt/c/run_raspagui.bat 파일을 Windows에서 실행하면"
echo "WSL에서 장고 서버가 자동으로 실행되고 브라우저가 열립니다."
echo "만약 경로가 다르다면 .bat 파일의 set WSL_PROJECT_PATH 부분을 직접 수정해 주세요."
