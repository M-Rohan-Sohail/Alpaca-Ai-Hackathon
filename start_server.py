import os
import subprocess
import sys
import time

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")
    
    print("🚀 Starting Alpaca Trading Terminal 🚀")
    
    # 1. Start the FastAPI Server (which automatically starts the Daemon)
    api_script = os.path.join(base_dir, "api_server.py")
    print(f"🔧 Starting API Server: {api_script}")
    api_process = subprocess.Popen(
        [sys.executable, api_script],
        cwd=base_dir
    )
    
    # 2. Wait a moment for API to initialize
    time.sleep(2)
    
    # 3. Start the Next.js Frontend
    # Use npm from the agentic_env bin directory since we installed nodeenv there
    npm_path = os.path.join(os.path.dirname(sys.executable), "npm")
    if not os.path.exists(npm_path):
        # Fallback to system npm if not found in virtualenv
        npm_path = "npm"
        
    print(f"🎨 Starting Frontend Server (npm run dev)...")
    env = os.environ.copy()
    agentic_bin = os.path.dirname(sys.executable)
    env["PATH"] = f"{agentic_bin}:{env.get('PATH', '')}"
    try:
        frontend_process = subprocess.Popen(
            [npm_path, "run", "dev"],
            cwd=frontend_dir,
            env=env
        )
    except FileNotFoundError:
        print(f"❌ Could not find npm at {npm_path}. Make sure Node.js is installed.")
        api_process.terminate()
        sys.exit(1)
        
    print("\n✅ All servers started successfully!")
    print("🌍 Dashboard: http://localhost:3000")
    print("📡 API Server: http://localhost:8000")
    print("\nPress Ctrl+C to stop all servers.")
    
    try:
        # Keep the main process alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        api_process.terminate()
        frontend_process.terminate()
        api_process.wait()
        frontend_process.wait()
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
