import os
import subprocess
import sys
import time

def run_script(script_path: str):
    if not os.path.exists(script_path):
        print(f"\n❌ ERROR: Script not found at {script_path}")
        sys.exit(1)
        
    print(f"\n{'='*50}")
    print(f"🚀 RUNNING: {os.path.basename(script_path)}")
    print(f"{'='*50}")
    
    python_exe = sys.executable
    
    try:
        subprocess.run(
            [python_exe, script_path],
            cwd=os.path.dirname(script_path),
            check=True
        )
        print(f"\n✅ SUCCESS: {os.path.basename(script_path)} completed.\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ FAILED: {os.path.basename(script_path)} crashed with exit code {e.returncode}.")
        print("Pipeline aborted.")
        sys.exit(1)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    pipeline = [
        os.path.join(base_dir, "Data-Ingestion", "run_ingestion.py"),
        os.path.join(base_dir, "Data-Processing", "run_processing.py"),
        os.path.join(base_dir, "Deterministic-Filter", "deterministic_filter.py"),
        os.path.join(base_dir, "Market-Agent", "market_agent.py"),
        os.path.join(base_dir, "News Agent", "news_agent.py"),
        os.path.join(base_dir, "Options-Agent", "options_agent.py"),
        os.path.join(base_dir, "Decision-agent", "decision_agent.py"),
        os.path.join(base_dir, "Risk Assessment Engine", "risk_engine.py"),
        os.path.join(base_dir, "Execution Agent", "execution_agent.py")
    ]
    
    print("🌟 STARTING FULL AGENTIC PIPELINE 🌟")
    print(f"Total steps: {len(pipeline)}")
    
    start_time = time.time()
    
    for script in pipeline:
        run_script(script)
        
    elapsed = time.time() - start_time
    print(f"{'='*50}")
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS! 🎉")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
