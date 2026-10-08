import streamlit.web.cli as stcli
import sys
import os
import threading
import time
import socket
import webview

def resolve_path(path):
    # PyInstaller extracts files to a temporary folder stored in sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.abspath(os.path.join(os.getcwd(), path))

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def start_streamlit():
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--server.headless", "true",
        "--global.developmentMode=false",
    ]
    try:
        stcli.main()
    except SystemExit:
        pass

if __name__ == "__main__":
    t = threading.Thread(target=start_streamlit)
    t.daemon = True
    t.start()

    # Wait for the server to start
    timeout = 30
    start_time = time.time()
    while not check_port(8501):
        if time.time() - start_time > timeout:
            sys.exit(1)
        time.sleep(0.5)
        
    # Streamlit binds the TCP port slightly before the HTTP server is actually ready to serve pages.
    # Adding a hard delay prevents PyWebView from throwing ERR_CONNECTION_REFUSED.
    time.sleep(3)

    webview.create_window('Lamhe Asset Forge', 'http://localhost:8501', width=1280, height=800)
    webview.start()
    os._exit(0)
