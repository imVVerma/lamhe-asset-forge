import webview
import threading
import subprocess
import time
import socket
import sys
import os

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def start_streamlit():
    env = os.environ.copy()
    # Path to streamlit executable or run via python -m
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true"]
    
    # Hide console window on Windows
    kwargs = {}
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'] = startupinfo
        
    subprocess.Popen(cmd, env=env, **kwargs)

def main():
    # Start the Streamlit server in the background
    t = threading.Thread(target=start_streamlit)
    t.daemon = True
    t.start()

    # Wait for the server to start (timeout after 30 seconds)
    timeout = 30
    start_time = time.time()
    while not check_port(8501):
        if time.time() - start_time > timeout:
            sys.exit(1)
        time.sleep(0.5)

    # Create the native window
    webview.create_window('Lamhe Asset Forge', 'http://localhost:8501', width=1280, height=800)
    webview.start()

if __name__ == '__main__':
    main()
