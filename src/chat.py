"""通过 OpenAI 兼容接口运行一次流式对话。"""

import argparse
import json
from pathlib import Path
import socket
import sys
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]


class ChatError(Exception):
    """可以向用户展示的错误；不包含密钥或原始响应。"""


def load_config(path):
    if not path.exists():
        raise ChatError("缺少 .env，请参照 .env.example 创建。")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ChatError(".env 格式错误，应使用 KEY=value。")
        values[key.strip()] = value.strip().strip("\"'")
    for key in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"):
        if not values.get(key):
            raise ChatError(f".env 缺少 {key}。")
    if not values["OPENAI_BASE_URL"].startswith(("http://", "https://")):
        raise ChatError("OPENAI_BASE_URL 必须使用 http:// 或 https://。")
    return values


def stream_chat(config, prompt, timeout=30):
    payload = {
        "model": config["OPENAI_MODEL"],
        "messages": [
            {"role": "system", "content": "你是一个友好的助手，请用中文回答。"},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }
    req = request.Request(
        config["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + config["OPENAI_API_KEY"],
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type.lower():
                raise ChatError("接口未返回 SSE 流，请检查 stream 支持情况。")
            event_lines = []
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if line.startswith("data:"):
                    event_lines.append(line[5:].lstrip(" "))
                elif not line and event_lines:
                    data = "\n".join(event_lines)
                    event_lines.clear()
                    if data == "[DONE]":
                        return
                    event = json.loads(data)
                    if not isinstance(event, dict) or "error" in event:
                        raise ChatError("接口返回了流式错误事件。")
                    choices = event.get("choices", [])
                    if not isinstance(choices, list):
                        raise ChatError("流式响应的 choices 格式错误。")
                    if not choices:
                        continue
                    content = choices[0].get("delta", {}).get("content")
                    if content is not None:
                        if not isinstance(content, str):
                            raise ChatError("流式响应的 content 格式错误。")
                        yield content
            raise ChatError("响应流提前结束，未收到 [DONE]；已显示的回答可能不完整。")
    except error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ChatError(f"认证或访问被拒绝（HTTP {exc.code}），请检查 Token 和权限。") from None
        raise ChatError(f"接口请求失败（HTTP {exc.code}）。") from None
    except (TimeoutError, socket.timeout):
        raise ChatError("请求超时，已显示的回答可能不完整。") from None
    except error.URLError:
        raise ChatError("无法连接接口，请检查网络和接口地址。") from None
    except (ValueError, UnicodeError, AttributeError, TypeError, IndexError):
        raise ChatError("接口响应格式错误，无法解析流式回答。") from None
    except OSError:
        raise ChatError("网络读取失败，已显示的回答可能不完整。") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="你好，请介绍一下自己。")
    parser.add_argument("--timeout", type=float, default=30, help="网络读取超时秒数，默认 30")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    try:
        config = load_config(ROOT / ".env")
        print(f"[模型调用] 开始 model={config['OPENAI_MODEL']}", file=sys.stderr)
        for chunk in stream_chat(config, args.prompt, args.timeout):
            print(chunk, end="", flush=True)
        print()
        print("[模型调用] 完成", file=sys.stderr)
        return 0
    except (ChatError, OSError) as exc:
        message = str(exc) if isinstance(exc, ChatError) else "无法读取 .env，请检查文件权限。"
        print(f"\n[模型调用] 失败：{message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[模型调用] 已取消", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
