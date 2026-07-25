from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

def parse_box_header(data, offset):
    if offset + 8 > len(data):
        return None, 0, 0
    size = int.from_bytes(data[offset:offset+4], 'big')
    btype = data[offset+4:offset+8]
    if size == 1:
        if offset + 16 > len(data):
            return None, 0, 0
        size = int.from_bytes(data[offset+8:offset+16], 'big')
        hlen = 16
    else:
        hlen = 8
    return btype, size, hlen

def find_sub_box(data, target_type):
    offset = 0
    while offset + 8 <= len(data):
        btype, size, hlen = parse_box_header(data, offset)
        if not btype or size < hlen or offset + size > len(data):
            break
        if btype == target_type:
            return data[offset + hlen : offset + size]
        offset += size
    return None

def find_all_sub_boxes(data, target_type):
    boxes = []
    offset = 0
    while offset + 8 <= len(data):
        btype, size, hlen = parse_box_header(data, offset)
        if not btype or size < hlen or offset + size > len(data):
            break
        if btype == target_type:
            boxes.append(data[offset + hlen : offset + size])
        offset += size
    return boxes

def get_real_mp4_meta(video_url):
    fps = None
    width = None
    height = None
    
    try:
        req = urllib.request.Request(video_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Range': 'bytes=0-524288'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()

        if b'moov' not in data:
            req_end = urllib.request.Request(video_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Range': 'bytes=-524288'
            })
            with urllib.request.urlopen(req_end, timeout=5) as resp_end:
                data += resp_end.read()

        moov_idx = data.find(b'moov')
        if moov_idx != -1:
            moov_box_start = max(0, moov_idx - 4)
            moov_size = int.from_bytes(data[moov_box_start:moov_box_start+4], 'big')
            
            if moov_size < 8 or moov_box_start + moov_size > len(data):
                moov_data = data[moov_idx + 4:]
            else:
                moov_data = data[moov_idx + 4 : moov_box_start + moov_size]

            traks = find_all_sub_boxes(moov_data, b'trak')

            for trak in traks:
                mdia = find_sub_box(trak, b'mdia')
                if not mdia:
                    continue
                
                hdlr = find_sub_box(mdia, b'hdlr')
                if not hdlr or len(hdlr) < 12:
                    continue
                
                handler_type = hdlr[8:12]
                if handler_type != b'vide':
                    continue

                # 1. Ambil Timescale dari Video Track
                mdhd = find_sub_box(mdia, b'mdhd')
                timescale = None
                if mdhd and len(mdhd) >= 16:
                    version = mdhd[0]
                    if version == 1 and len(mdhd) >= 20:
                        timescale = int.from_bytes(mdhd[16:20], 'big')
                    elif version == 0:
                        timescale = int.from_bytes(mdhd[12:16], 'big')

                # 2. Ambil Resolusi (Width & Height) Presisi (Mendukung hingga 2K / 4K / 8K)
                tkhd = find_sub_box(trak, b'tkhd')
                if tkhd and len(tkhd) >= 84:
                    version = tkhd[0]
                    if version == 1 and len(tkhd) >= 96:
                        w = int.from_bytes(tkhd[88:92], 'big') >> 16
                        h = int.from_bytes(tkhd[92:96], 'big') >> 16
                    elif version == 0:
                        w = int.from_bytes(tkhd[76:80], 'big') >> 16
                        h = int.from_bytes(tkhd[80:84], 'big') >> 16
                    else:
                        w, h = None, None
                    
                    if w and h and 100 <= w <= 8192 and 100 <= h <= 8192:
                        width, height = w, h

                # 3. Ambil FPS dari stts Video Track
                minf = find_sub_box(mdia, b'minf')
                stbl = find_sub_box(minf, b'stbl') if minf else None
                stts = find_sub_box(stbl, b'stts') if stbl else None

                if stts and len(stts) >= 8 and timescale and timescale > 0:
                    entry_count = int.from_bytes(stts[4:8], 'big')
                    fps_counts = {}
                    off = 8

                    for _ in range(min(entry_count, 1000)):
                        if off + 8 > len(stts):
                            break
                        s_count = int.from_bytes(stts[off:off+4], 'big')
                        s_delta = int.from_bytes(stts[off+4:off+8], 'big')
                        off += 8

                        if s_delta > 0:
                            calc_fps = round(timescale / s_delta)
                            if 15 <= calc_fps <= 240:
                                fps_counts[calc_fps] = fps_counts.get(calc_fps, 0) + s_count

                    if fps_counts:
                        fps = max(fps_counts.items(), key=lambda x: x[1])[0]

                break

    except Exception:
        pass

    return fps, width, height


# HTML UI Frontend
HTML_UI = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Parsgus — TikTok Metadata & Stream Analyzer</title>
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
    body { 
      background-color: var(--bg-color); 
      color: var(--text-main); 
      display: flex; 
      flex-direction: column; 
      align-items: center; 
      min-height: 100vh; 
      padding: 20px; 
    }
    header { 
      width: 100%; 
      max-width: 440px; 
      padding: 24px 0 16px; 
      text-align: center; 
      border-bottom: 1px solid var(--border-color); 
      margin-bottom: 24px; 
    }
    header h1 { 
      font-size: 2.2rem; 
      font-weight: 800; 
      color: var(--accent-green); 
      letter-spacing: -0.5px; 
    }
    header p { 
      font-size: 0.85rem; 
      color: var(--text-muted); 
      margin-top: 4px; 
    }
    .social-links {
      margin-top: 10px;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .social-links a {
      color: var(--accent-green);
      text-decoration: none;
      font-weight: 700;
      transition: all 0.2s ease;
      border-bottom: 1px dashed var(--accent-green);
    }
    .social-links a:hover {
      color: #34d399;
      border-bottom-style: solid;
    }
    .container { width: 100%; max-width: 440px; }
    .card { 
      background: var(--card-bg); 
      border: 1px solid var(--border-color); 
      border-radius: 16px; 
      padding: 24px; 
      box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
    }
    .input-group { display: flex; flex-direction: column; gap: 12px; }
    label { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
    input[type="text"] { 
      width: 100%; 
      padding: 14px 16px; 
      background: #0b0f12; 
      border: 1px solid var(--border-color); 
      border-radius: 10px; 
      color: var(--text-main); 
      font-size: 0.95rem; 
      outline: none; 
      transition: border-color 0.2s; 
    }
    input[type="text"]:focus { border-color: var(--accent-green); }
    button { 
      width: 100%; 
      padding: 14px; 
      background: var(--accent-green); 
      color: #0b0f12; 
      font-size: 0.95rem; 
      font-weight: 700; 
      border: none; 
      border-radius: 10px; 
      cursor: pointer; 
      transition: all 0.2s; 
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.2);
    }
    button:hover { 
      background: var(--accent-green-hover); 
      transform: translateY(-1px);
    }
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
    <h1>Parsgus</h1>
    <p>TikTok Metadata & Stream Analyzer</p>
    <div class="social-links">
      follow <a href="https://tiktok.com/@parsgus" target="_blank" rel="noopener">TikTok</a> and join <a href="https://t.me/parsgus" target="_blank" rel="noopener">Telegram</a>
    </div>
  </header>

  <main class="container">
    <div class="card">
      <div class="input-group">
        <label for="url">TikTok Video URL</label>
        <input type="text" id="url" placeholder="https://vt.tiktok.com/xxxx/">
        <button onclick="getMetadata()">Ambil Statistik</button>
      </div>

      <div class="loading" id="loading">⚡ Menganalisis stream header video...</div>

      <div class="result" id="resultCard">
        <h3>Statistik Video</h3>
        <div class="row"><span>Uploader</span> <strong id="uploader">-</strong></div>
        <div class="row"><span>Resolusi</span> <strong id="res">-</strong></div>
        <div class="row"><span>Frame Rate (FPS)</span> <strong id="fps">-</strong></div>
        <div class="row"><span>Bitrate</span> <strong id="bitrate">-</strong></div>
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
        document.getElementById('bitrate').innerText = data.bitrate;
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
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_UI.encode('utf-8'))

    def do_POST(self):
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
            video_stream_url = info.get('hdplay') or info.get('play')
            
            api_width = info.get('width', 0)
            api_height = info.get('height', 0)
            
            final_width = api_width
            final_height = api_height
            real_fps = 30

            if video_stream_url:
                parsed_fps, parsed_w, parsed_h = get_real_mp4_meta(video_stream_url)
                if parsed_fps:
                    real_fps = parsed_fps
                if parsed_w and parsed_h:
                    final_width = parsed_w
                    final_height = parsed_h

            if not final_width or final_width < 100 or final_width > 8192:
                final_width = api_width if api_width > 0 else 1080
            if not final_height or final_height < 100 or final_height > 8192:
                final_height = api_height if api_height > 0 else 1920

            filesize_bytes = info.get('hd_size', 0) or info.get('size', 0) or info.get('wm_size', 0)
            filesize_mb = round(filesize_bytes / (1024 * 1024), 2) if filesize_bytes else "N/A"
            duration = info.get('duration', 0)

            bitrate_str = "-"
            if filesize_bytes > 0 and duration > 0:
                calc_bitrate_kbps = round((filesize_bytes * 8) / (duration * 1000))
                if calc_bitrate_kbps >= 1000:
                    bitrate_str = f"{round(calc_bitrate_kbps / 1000, 2)} Mbps"
                else:
                    bitrate_str = f"{calc_bitrate_kbps} kbps"

            result = {
                'uploader': info.get('author', {}).get('nickname', '-'),
                'username': info.get('author', {}).get('unique_id', '-'),
                'title': info.get('title', '-'),
                'width': final_width,
                'height': final_height,
                'fps': real_fps,
                'bitrate': bitrate_str,
                'duration': duration,
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
                        
