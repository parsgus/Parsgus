from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url', '').strip()

            if not url:
                self._send_json({'error': 'URL tidak boleh kosong'}, 400)
                return

            # Menggunakan API parser eksternal yang aman dari blokir IP Vercel
            api_endpoint = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url)}"
            
            req = urllib.request.Request(
                api_endpoint, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))

            # Cek respon dari API
            if res_data.get('code') != 0 or 'data' not in res_data:
                self._send_json({'error': 'Gagal mengambil data. Pastikan link video TikTok publik.'}, 400)
                return

            info = res_data['data']
            filesize_bytes = info.get('size', 0) or info.get('wm_size', 0)
            filesize_mb = round(filesize_bytes / (1024 * 1024), 2) if filesize_bytes else "N/A"

            # Format data untuk dikirim ke frontend
            result = {
                'uploader': info.get('author', {}).get('nickname', '-'),
                'username': info.get('author', {}).get('unique_id', '-'),
                'title': info.get('title', '-'),
                'width': info.get('width', 576),
                'height': info.get('height', 576),
                'fps': 30, # Standar FPS TikTok
                'duration': info.get('duration', 0),
                'filesize_mb': filesize_mb,
                'ext': 'MP4'
            }

            self._send_json(result, 200)

        except Exception as e:
            self._send_json({'error': f"Sistem Error: {str(e)}"}, 500)

    def _send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
            
