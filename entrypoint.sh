#!/bin/bash
# Sealos Devbox 发布启动脚本
cd "$(dirname "$0")/backend"
pip install -r requirements.txt --quiet
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000
