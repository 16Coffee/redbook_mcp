#!/bin/bash
cd "$(dirname "$0")"  # 自动切换到脚本所在目录
python main.py --stdio
chmod +x run_xhs.sh
