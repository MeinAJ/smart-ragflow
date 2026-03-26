#!/usr/bin/env python3
"""
一键启动所有服务。

启动顺序：
1. Backend Admin (端口 8001) - 文档管理服务
2. Client API (端口 8000) - 问答服务
3. Parser Worker - 后台解析服务
4. Frontend QA (端口 3000) - 问答前端
5. Frontend Admin (端口 3001) - 管理后台前端

用法：
    python start_all.py
    
或者分别启动：
    python start_all.py --services admin
    python start_all.py --services qa
    python start_all.py --services parser
    python start_all.py --services frontend_qa
    python start_all.py --services frontend_admin
    
启动所有后端服务：
    python start_all.py --services backend
    
启动所有前端服务：
    python start_all.py --services frontend
"""

import os
import sys
import argparse
import subprocess
import time
import shutil
import socket
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
    print("🚀 Starting QA API (port 8000)...")
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


def start_frontend_qa():
    """启动 Frontend QA 前端服务。"""
    print("🚀 Starting Frontend QA (port 3000)...")
    frontend_dir = Path(__file__).parent / "frontend_QA"
    if not frontend_dir.exists():
        print(f"❌ Frontend QA directory not found: {frontend_dir}")
        return None
    
    # 检查 node_modules 是否存在
    if not (frontend_dir / "node_modules").exists():
        print("⚠️  node_modules not found. Please run 'npm install' in frontend_QA first.")
        return None
    
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        env=os.environ
    )


def start_frontend_admin():
    """启动 Frontend Admin 前端服务。"""
    print("🚀 Starting Frontend Admin (port 3001)...")
    frontend_dir = Path(__file__).parent / "frontend_admin"
    if not frontend_dir.exists():
        print(f"❌ Frontend Admin directory not found: {frontend_dir}")
        return None
    
    # 检查 node_modules 是否存在
    if not (frontend_dir / "node_modules").exists():
        print("⚠️  node_modules not found. Please run 'npm install' in frontend_admin first.")
        return None
    
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        env=os.environ
    )


def check_npm():
    """检查 npm 是否可用。"""
    return shutil.which("npm") is not None


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查指定端口是否已开放（服务是否就绪）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def wait_for_service(name: str, host: str, port: int, max_wait: int = 60) -> bool:
    """
    等待服务启动就绪。
    
    Args:
        name: 服务名称
        host: 主机地址
        port: 端口号
        max_wait: 最大等待时间（秒）
    
    Returns:
        bool: 服务是否成功启动
    """
    print(f"⏳  Waiting for {name} to be ready...", end="", flush=True)
    start_time = time.time()
    check_interval = 0.5
    dots = 0
    
    while time.time() - start_time < max_wait:
        if check_port_open(host, port):
            elapsed = time.time() - start_time
            print(f" ✓ (ready in {elapsed:.1f}s)")
            return True
        time.sleep(check_interval)
        dots += 1
        if dots % 4 == 0:
            print("\b\b\b   \b\b\b", end="", flush=True)
        else:
            print(".", end="", flush=True)
    
    print(" ✗ (timeout)")
    return False


def wait_for_process(proc: subprocess.Popen, name: str, max_wait: int = 10) -> bool:
    """
    等待进程启动（用于没有 HTTP 端口的服务）。
    
    Args:
        proc: 进程对象
        name: 服务名称
        max_wait: 最大等待时间（秒）
    
    Returns:
        bool: 进程是否正常运行
    """
    print(f"⏳  Waiting for {name} to start...", end="", flush=True)
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # 检查进程是否还在运行
        ret = proc.poll()
        if ret is None:
            # 进程仍在运行，认为启动成功
            elapsed = time.time() - start_time
            print(f" ✓ (ready in {elapsed:.1f}s)")
            return True
        else:
            # 进程已退出，启动失败
            print(f" ✗ (exited with code {ret})")
            return False
        time.sleep(0.1)
    
    # 超时但进程仍在运行
    print(" ✓ (running)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Start Smart RAGFlow services")
    parser.add_argument(
        "--services",
        nargs="+",
        choices=["admin", "qa", "parser", "frontend_qa", "frontend_admin", "backend", "frontend", "all"],
        default=["all"],
        help="Services to start (default: all). 'backend'=admin+qa+parser, 'frontend'=frontend_qa+frontend_admin"
    )
    args = parser.parse_args()

    services = args.services
    if "all" in services:
        services = ["admin", "qa", "parser", "frontend_qa", "frontend_admin"]
    elif "backend" in services:
        services = [s for s in services if s != "backend"]
        if "admin" not in services:
            services.append("admin")
        if "qa" not in services:
            services.append("qa")
        if "parser" not in services:
            services.append("parser")
    elif "frontend" in services:
        services = [s for s in services if s != "frontend"]
        if "frontend_qa" not in services:
            services.append("frontend_qa")
        if "frontend_admin" not in services:
            services.append("frontend_admin")

    # 检查是否需要启动前端服务，并验证 npm
    need_frontend = "frontend_qa" in services or "frontend_admin" in services
    if need_frontend and not check_npm():
        print("❌ npm not found. Please install Node.js first.")
        print("   Visit: https://nodejs.org/")
        return

    processes = []
    started_services = []  # 记录成功启动的服务

    try:
        # 先启动后端服务
        if "admin" in services:
            proc = start_admin()
            processes.append(("admin", proc))
            if wait_for_service("Admin API", "localhost", 8001, max_wait=60):
                started_services.append("admin")
            else:
                print(f"⚠️  Admin API may not be fully ready, continuing anyway...")

        if "qa" in services:
            proc = start_client()
            processes.append(("qa", proc))
            if wait_for_service("QA API", "localhost", 8000, max_wait=60):
                started_services.append("qa")
            else:
                print(f"⚠️  QA API may not be fully ready, continuing anyway...")

        if "parser" in services:
            proc = start_parser()
            processes.append(("parser", proc))
            if wait_for_process(proc, "Parser Worker", max_wait=10):
                started_services.append("parser")
            else:
                print(f"⚠️  Parser Worker may not be fully ready, continuing anyway...")

        # 再启动前端服务
        if "frontend_qa" in services:
            proc = start_frontend_qa()
            if proc:
                processes.append(("frontend_qa", proc))
                if wait_for_service("Frontend QA", "localhost", 3000, max_wait=60):
                    started_services.append("frontend_qa")
                else:
                    print(f"⚠️  Frontend QA may not be fully ready, continuing anyway...")
            else:
                print(f"⚠️  Failed to start Frontend QA")

        if "frontend_admin" in services:
            proc = start_frontend_admin()
            if proc:
                processes.append(("frontend_admin", proc))
                if wait_for_service("Frontend Admin", "localhost", 3001, max_wait=60):
                    started_services.append("frontend_admin")
                else:
                    print(f"⚠️  Frontend Admin may not be fully ready, continuing anyway...")
            else:
                print(f"⚠️  Failed to start Frontend Admin")

        print("\n" + "="*50)
        print("✅ All services started!")
        print("="*50)

        if "admin" in started_services:
            print("- Admin API:      http://localhost:8001")
        if "qa" in started_services:
            print("- QA API:         http://localhost:8000")
        if "frontend_qa" in started_services:
            print("- Frontend QA:    http://localhost:3000")
        if "frontend_admin" in started_services:
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
