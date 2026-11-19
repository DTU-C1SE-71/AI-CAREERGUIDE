"""HTTP stub tổng hợp phục vụ browser test, chỉ bind loopback."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def do_POST(self):
        length=int(self.headers.get("Content-Length",0))
        if length>2*1024*1024:
            self.send_error(413);return
        self.rfile.read(length)
        raw=json.dumps({"choices":[{"message":{"content":"OK"}}]}).encode()
        self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        raw=b'{"data":[{"id":"audit-model"}]}'
        self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",18081),Handler)
    print("Synthetic loopback stub ready on port18081",flush=True)
    server.serve_forever()
