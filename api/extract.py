from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

# Tampilan HTML Halaman Depan
HTML_UI = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>parsgus — TikTok Metadata Analyzer</title>
  <style>
    :root {
      --bg-color: #0b0f12;
      --card-bg: #151a21;
      --accent-green: #10b981;
      --accent-green-hover: #059669;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --border-color: #222933;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
    body { background-color: var(--bg-color); color: var(--text-main); display: flex; flex-direction: column; align-items: center; min-height: 100vh; padding: 20px; }
    header { width: 100%; max-width: 440px; padding: 24px 0 16px; text-align: center; border-bottom: 1px solid var(--border-color); margin-bottom: 24px; }
    header h1 { font-size: 2rem; font-weight: 800; color: var(--accent-green); letter-spacing: -0.5px; text-transform: lowercase; }
    header p { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }
    .container { width: 100%; max-width: 440px; }
    .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
    .input-group { display: flex; flex-direction: column; gap: 12px; }
    label { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    input[type="text"] { width: 100%; padding: 14px 16px; background: #0b0f12; border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-main); font-size: 0.95rem; outline: none; transition: border-color 0.2s; }
    input[type="text"]:focus { border-color: var(--accent-green); }
    button { width: 100%; padding: 14px; background: var(--accent-green); color: #0b0f12; font-size: 0.95rem; font-weight: 700; border: none; border-radius: 10px; cursor: pointer; transition: background 0.2s; }
    button:hover { background: var(--accent-green-hover); }
    .loading { display: none; text-align: center; margin-top: 20px; color: var(--accent-green); font-size: 0.9rem; font-weight: 600; }
    .result { display: none; margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border-color); }
    .result h3 { font-size: 0.85rem; color: var(--accent-green); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.8px; }
    .row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px dashed var(--border-color); font-size: 0.9rem; }
    .row:last-child { border-bottom: none; }
    .row span { color: var(--text-muted); }
    .row strong { color: var(--text-main); font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <h1>parsgus</h1>
    <p>TikTok Metadata & Stream Analyzer</p>
  </header>

  <main class="container">
    <div class="card">
      <div class="input-group">
        <label for="url">TikTok Video URL</label>
        <input type="text" id="url" placeholder="https://vt.tiktok.com/xxxx/">
        <button onclick="getMetadata()">Ambil Statistik</button>
      </div>

      <div class="loading" id="loading">⚡ Mengambil data dari server...</div>

      <div class="result" id="resultCard">
        <h3>Statistik Video</h3>
        <div class="row"><span>Uploader</span> <strong id="uploader">-</strong></div>
        <div class="row"><span>Resolusi</span> <strong id="res">-</strong></div>
        <div class="row"><span>Frame Rate (FPS)</span> <strong id="fps">-</strong></div>
        <div class="row"><span>Durasi</span> <strong id="duration">-</strong></div>
        <div class="row"><span>Ukuran File</span> <strong id="filesize">-</strong></div>
        <div class="row"><span>Format</span> <strong id="format">-</strong></div>
      </div>
    </div>
  </main>

  <script>
    async function getMetadata() {
      const urlInput = document.getElementById('url').value.trim();
      if (!urlInput) {
        alert("Masukkan URL TikTok terlebih dahulu!");
        return;
      }

      const loading = document.getElementById('loading');
      const resultCard = document.getElementById('resultCard');

      loading.style.display = 'block';
      resultCard.style.display = 'none';

      try {
        const res = await fetch('/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: urlInput })
        });

        const data = await res.json();
        loading.style.display = 'none';

        if (data.error) {
          alert("Error: " + data.error);
          return;
        }

        document.getElementById('uploader').innerText = `${data.uploader} (@${data.username})`;
        document.getElementById('res').innerText = `${data.width} x ${data.height}`;
        document.getElementById('fps').innerText = `${data.fps} fps`;
        document.getElementById('duration').innerText = `${data.duration}s`;
        document.getElementById('filesize').innerText = `~${data.filesize_mb} MB`;
        document.getElementById('format').innerText = (data.ext || 'MP4').toUpperCase();

        resultCard.style.display = 'block';

      } catch (e) {
        loading.style.display = 'none';
        alert("Gagal terhubung ke API server.");
      }
    }
  </script>
</body>
</html>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Menampilkan tampilan UI HTML saat dibuka di browser
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_UI.encode('utf-8'))

    def do_POST(self):
        # Proses ekstraksi metadata video
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url', '').strip()

            if not url:
                self._send_json({'error': 'URL tidak boleh kosong'}, 400)
                return

            api_endpoint = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url)}"
            
            req = urllib.request.Request(
                api_endpoint, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))

            if res_data.get('code') != 0 or 'data' not in res_data:
                self._send_json({'error': 'Gagal mengambil data. Pastikan link video TikTok publik.'}, 400)
                return

            info = res_data['data']
            filesize_bytes = info.get('size', 0) or info.get('wm_size', 0)
            filesize_mb = round(filesize_bytes / (1024 * 1024), 2) if filesize_bytes else "N/A"

            result = {
                'uploader': info.get('author', {}).get('nickname', '-'),
                'username': info.get('author', {}).get('unique_id', '-'),
                'title': info.get('title', '-'),
                'width': info.get('width', 576),
                'height': info.get('height', 576),
                'fps': 30,
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
            
