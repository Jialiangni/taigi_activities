"""
本機網頁預覽伺服器 (Local Web Server)
執行此腳本即可在本機瀏覽網頁版，並支援區域網路 (手機/平板) 共同瀏覽
"""
import http.server
import socketserver
import webbrowser
import socket

PORT = 8080


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 允許跨域與快取控制
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def main():
    local_ip = get_local_ip()
    local_url = f"http://localhost:{PORT}"
    network_url = f"http://{local_ip}:{PORT}"

    print("=" * 60)
    print("🎭 北北桃台語活動行事曆 - 網頁版預覽伺服器啟動中...")
    print(f"👉 本機瀏覽網址：   {local_url}")
    print(f"📱 區網/手機瀏覽：  {network_url}")
    print("=" * 60)
    print("按 Ctrl + C 可隨時停止伺服器\n")

    # 自動開啟瀏覽器
    webbrowser.open(local_url)

    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 網頁伺服器已停止。")


if __name__ == "__main__":
    main()
