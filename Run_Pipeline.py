import os
import subprocess
import sys
import time

def run_script(script_path: str, args: list = None, max_retries: int = 1):
    if not os.path.exists(script_path):
        print(f"\n❌ ERROR: Script not found at {script_path}")
        sys.exit(1)
        
    print(f"\n{'='*50}")
    print(f"🚀 RUNNING: {os.path.basename(script_path)} {' '.join(args or [])}")
    print(f"{'='*50}")
    
    python_exe = sys.executable
    cmd = [python_exe, script_path] + (args or [])
    
    for attempt in range(max_retries):
        try:
            subprocess.run(
                cmd,
                cwd=os.path.dirname(script_path),
                check=True
            )
            print(f"\n✅ SUCCESS: {os.path.basename(script_path)} completed.\n")
            return
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                print(f"\n⚠️ WARNING: {os.path.basename(script_path)} crashed with exit code {e.returncode}. Retrying ({attempt+2}/{max_retries})...")
            else:
                print(f"\n❌ FAILED: {os.path.basename(script_path)} crashed with exit code {e.returncode}.")
                print("Pipeline aborted.")
                sys.exit(1)


def cleanup_save_data(base_dir):
    save_data_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT")
    if not os.path.exists(save_data_dir):
        return
        
    print(f"\n🧹 Cleaning up old JSON files in {save_data_dir} (except Execution and Trade Journal)")
    count = 0
    for root, dirs, files in os.walk(save_data_dir):
        if "Execution-Agent-Output" in root or "Trade-Journal-Output" in root:
            continue
        for file in files:
            if file.endswith(".json"):
                os.remove(os.path.join(root, file))
                count += 1
    print(f"✅ Cleaned up {count} old JSON files.")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run cleanup before starting pipeline
    cleanup_save_data(base_dir)
    
    pipeline = [
        (os.path.join(base_dir, "Data-Ingestion", "run_ingestion.py"), []),
        (os.path.join(base_dir, "Data-Processing", "run_processing.py"), []),
        (os.path.join(base_dir, "Deterministic-Filter", "deterministic_filter.py"), []),
        (os.path.join(base_dir, "Market-Agent", "market_agent.py"), []),
        (os.path.join(base_dir, "News Agent", "news_agent.py"), []),
        (os.path.join(base_dir, "Options-Agent", "options_agent.py"), []),
        (os.path.join(base_dir, "Decision-agent", "decision_agent.py"), []),
        (os.path.join(base_dir, "Risk Assessment Engine", "risk_engine.py"), []),
        (os.path.join(base_dir, "Execution Agent", "execution_agent.py"), ["--entries-only"])
    ]
    
    print("🌟 STARTING FULL AGENTIC PIPELINE 🌟")
    print(f"Total steps: {len(pipeline)}")
    
    start_time = time.time()
    
    for script, args in pipeline:
        if "news_agent.py" in script:
            run_script(script, args, max_retries=3)
        else:
            run_script(script, args)
        
    # Launch Fast Exit Daemon as a background subprocess
    daemon_script = os.path.join(base_dir, "fast_exit_daemon.py")
    pid_file = os.path.join(base_dir, "fast_exit_daemon.pid")
    
    daemon_running = False
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            # Check if process is actually running
            os.kill(old_pid, 0)
            daemon_running = True
            print(f"\n🔄 Fast Exit Daemon is already running (PID: {old_pid}). Skipping launch.")
        except (ValueError, OSError):
            # Process is not running or PID file is invalid
            pass
            
    if not daemon_running:
        print("\n🚀 Launching Fast Exit Daemon as a Subprocess...")
        # Launch detached subprocess (Linux/Mac)
        subprocess.Popen(
            [sys.executable, daemon_script],
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        print("✅ Fast Exit Daemon is Running at Subprocess")
        
    elapsed = time.time() - start_time
    print(f"{'='*50}")
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS! 🎉")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
