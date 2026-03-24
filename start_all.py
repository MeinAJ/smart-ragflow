#!/usr/bin/env python3
"""
一键启动所有服务。

启动顺序：
1. Backend Admin (端口 8001) - 文档管理服务
2. Client API (端口 8000) - 问答服务
3. Parser Worker - 后台解析服务

用法：
    python start_all.py
    
或者分别启动：
    python start_all.py --services admin
    python start_all.py --services client
    python start_all.py --services parser
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path

def start_admin():
    """启动 Backend Admin 服务。"""
    print("🚀 Starting Backend Admin (port 8001)...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend_admin.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    )

def start_client():
    """启动 Client API 服务。"""
    print("🚀 Starting Client API (port 8000)...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend_QA.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    )

def start_parser():
    """启动 Parser Worker。"""
    print("🚀 Starting Parser Worker...")
    return subprocess.Popen(
        [sys.executable, "backend_parser/worker.py"],
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    )

def main():
    parser = argparse.ArgumentParser(description="Start Smart RAGFlow services")
    parser.add_argument(
        "--services",
        nargs="+",
        choices=["admin", "client", "parser", "all"],
        default=["all"],
        help="Services to start"
    )
    args = parser.parse_args()
    
    services = args.services
    if "all" in services:
        services = ["admin", "client", "parser"]
    
    processes = []
    
    try:
        if "admin" in services:
            processes.append(("admin", start_admin()))
            time.sleep(2)  # 等待服务启动
            
        if "client" in services:
            processes.append(("client", start_client()))
            time.sleep(2)
            
        if "parser" in services:
            processes.append(("parser", start_parser()))
        
        print("\n✅ All services started!")
        print("- Admin API:    http://localhost:8001")
        print("- Client API:   http://localhost:8000")
        print("- Frontend QA:  http://localhost:3000")
        print("- Frontend Admin: http://localhost:3001")
        print("\nPress Ctrl+C to stop all services\n")
        
        # 等待所有进程
        for name, proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all services...")
        for name, proc in processes:
            print(f"  Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("✅ All services stopped")

if __name__ == "__main__":
    main()
