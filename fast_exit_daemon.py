import os
import sys
import time
import json
import subprocess

PID_FILE = "fast_exit_daemon.pid"
SLEEP_INTERVAL = 30
MAX_EMPTY_CHECKS = 3

def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def has_active_trades(base_dir):
    journal_path = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Trade-Journal-Output", "trade_journal.json")
    if not os.path.exists(journal_path):
        return False
        
    try:
        with open(journal_path, 'r') as f:
            data = json.load(f)
            
        open_trades = [t for t in data if isinstance(t, dict) and t.get("status") == "OPEN"]
        return len(open_trades) > 0
    except Exception as e:
        print(f"Error reading trade journal: {e}")
        return False

def run_script(script_path: str, args: list = None):
    if not os.path.exists(script_path):
        print(f"❌ ERROR: Script not found at {script_path}")
        return False
        
    python_exe = sys.executable
    cmd = [python_exe, script_path] + (args or [])
    
    try:
        subprocess.run(cmd, cwd=os.path.dirname(script_path), check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {os.path.basename(script_path)} crashed with exit code {e.returncode}.")
        return False

def main():
    write_pid()
    print("🚀 Fast Exit Daemon Started (PID: {})".format(os.getpid()))
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_script = os.path.join(base_dir, "Position-Monitor", "run_monitor.py")
    execution_script = os.path.join(base_dir, "Execution Agent", "execution_agent.py")
    
    empty_checks = 0
    
    try:
        while True:
            print("\n" + "="*40)
            print(f"🔍 Monitoring Cycle Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Step 1: Check active trades
            if has_active_trades(base_dir):
                print("✅ Active trades found. Running Monitor and Exits...")
                empty_checks = 0
                
                # Run the exit pipeline
                run_script(monitor_script)
                run_script(execution_script, ["--exits-only"])
            else:
                empty_checks += 1
                print(f"💤 No active trades found. (Empty checks: {empty_checks}/{MAX_EMPTY_CHECKS})")
                
                if empty_checks >= MAX_EMPTY_CHECKS:
                    print("🛑 No active trades for 3 consecutive checks. Self-terminating to save resources.")
                    break
                    
            print(f"⏳ Sleeping for {SLEEP_INTERVAL} seconds...")
            time.sleep(SLEEP_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n🛑 Fast Exit Daemon stopped manually.")
    finally:
        cleanup_pid()
        print("👋 Daemon shut down.")

if __name__ == "__main__":
    main()
