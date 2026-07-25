from http.server import BaseHTTPRequestHandler
import json
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Ambil panjang data request
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url', '')

            if not url:
                self._send_json({'error': 'URL tidak boleh kosong'}, 400)
                return

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filesize = info.get('filesize') or info.get('filesize_approx') or 0
                filesize_mb = round(filesize / (1024 * 1024), 2) if filesize else "N/A"

                result = {
                    'uploader': info.get('uploader', '-'),
                    'username': info.get('uploader_id', '-'),
                    'title': info.get('title', '-'),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'fps': info.get('fps', 0),
                    'duration': info.get('duration', 0),
                    'filesize_mb': filesize_mb,
                    'ext': info.get('ext', '-')
                }

                self._send_json(result, 200)

        except Exception as e:
            self._send_json({'error': f"Gagal mengekstrak: {str(e)}"}, 500)

    def _send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
