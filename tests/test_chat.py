"""使用本地 HTTP 服务验证协议和异常，不代表内网模型验证。"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import json

from src.chat import ChatError, load_config, stream_chat


@contextmanager
def serve(body, status=200, content_type="text/event-stream"):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {
        "OPENAI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
        "OPENAI_API_KEY": "test-only",
        "OPENAI_MODEL": "test-model",
    }
    try:
        yield config, received
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class ChatTests(unittest.TestCase):
    def test_stream_and_request(self):
        body = ': heartbeat\n\ndata: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        body += 'data: {"choices":[{"delta":{"content":"你好"}}]}\n\n'
        body += 'data: {"choices":[]}\n\ndata: [DONE]\n\n'
        with serve(body) as (config, received):
            self.assertEqual("".join(stream_chat(config, "问题")), "你好")
            path, payload = received[0]
            self.assertEqual(path, "/v1/chat/completions")
            self.assertTrue(payload["stream"])
            self.assertEqual(payload["messages"][-1]["content"], "问题")

    def test_auth_error_does_not_expose_response(self):
        with serve("private response", status=401) as (config, _):
            with self.assertRaisesRegex(ChatError, "HTTP 401") as caught:
                list(stream_chat(config, "问题"))
            self.assertNotIn("private response", str(caught.exception))
            self.assertNotIn(config["OPENAI_API_KEY"], str(caught.exception))

    def test_truncated_stream(self):
        with serve('data: {"choices":[{"delta":{"content":"部分"}}]}\n\n') as (config, _):
            chunks = stream_chat(config, "问题")
            self.assertEqual(next(chunks), "部分")
            with self.assertRaisesRegex(ChatError, "提前结束"):
                next(chunks)

    def test_invalid_event(self):
        with serve("data: invalid-json\n\n") as (config, _):
            with self.assertRaisesRegex(ChatError, "格式错误"):
                list(stream_chat(config, "问题"))

    def test_non_stream_response(self):
        with serve("{}", content_type="application/json") as (config, _):
            with self.assertRaisesRegex(ChatError, "未返回 SSE"):
                list(stream_chat(config, "问题"))

    def test_missing_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENAI_BASE_URL=http://localhost\nOPENAI_MODEL=test\n")
            with self.assertRaisesRegex(ChatError, "缺少 OPENAI_API_KEY"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
