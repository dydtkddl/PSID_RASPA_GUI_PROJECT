#!/bin/bash
set -e

# 1. Anaconda 설치 스크립트 다운로드
wget https://repo.anaconda.com/archive/Anaconda3-2023.09-0-Linux-x86_64.sh

# 2. Anaconda 설치 (비대화 모드, 설치 위치: $HOME/anaconda3)
bash Anaconda3-2023.09-0-Linux-x86_64.sh -b -p "$HOME/anaconda3"

# 3. PATH 설정
export PATH="$HOME/anaconda3/bin:$PATH"

# 4. .bashrc에 PATH 추가 (중복 방지)
grep -qxF 'export PATH="$HOME/anaconda3/bin:$PATH"' ~/.bashrc || \
  echo 'export PATH="$HOME/anaconda3/bin:$PATH"' >> ~/.bashrc

# 5. .bashrc 적용
source ~/.bashrc

echo "✅ Anaconda 설치 완료 및 환경 설정 적용됨"
