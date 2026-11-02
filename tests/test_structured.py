"""本地协议与输出边界测试，不代替真实模型验收。"""

import json
import unittest

from src.chat import ChatError
from src.structured import TASK_SCHEMA, extract_task, parse_task
from tests.test_chat import serve


def completion(content, finish_reason="stop", refusal=None):
    return json.dumps({"choices": [{
        "message": {"content": content, "refusal": refusal},
        "finish_reason": finish_reason,
    }]})


class StructuredTests(unittest.TestCase):
    def test_schema_request_and_valid_response(self):
        content = '{"title":"整理面试笔记","priority":"高"}'
        with serve(completion(content), content_type="application/json") as (config, received):
            self.assertEqual(extract_task(config, "高优先级：明天整理面试笔记"), json.loads(content))
            path, payload = received[0]
            self.assertEqual(path, "/v1/chat/completions")
            self.assertFalse(payload["stream"])
            self.assertEqual(payload["response_format"]["json_schema"]["schema"], TASK_SCHEMA)
            self.assertTrue(payload["response_format"]["json_schema"]["strict"])
            self.assertEqual(payload["messages"][-1]["content"], "高优先级：明天整理面试笔记")

    def test_invalid_json_and_fields(self):
        cases = [
            ("not-json", "不是合法 JSON"),
            ('```json\n{"title":"笔记","priority":"中"}\n```', "不是合法 JSON"),
            ('{"title":"笔记"}', "任务字段"),
            ('{"title":"笔记","priority":"中","extra":1}', "任务字段"),
            ('[]', "任务字段"),
            ('{"title":" ","priority":"中"}', "非空字符串"),
            ('{"title":1,"priority":"中"}', "非空字符串"),
            ('{"title":"笔记","priority":"紧急"}', "低、中、高"),
            ('{"title":"笔记","priority":[]}', "低、中、高"),
            (None, "未返回文本"),
        ]
        for content, expected in cases:
            with self.subTest(content=content):
                with self.assertRaisesRegex(ChatError, expected):
                    parse_task(content)

    def test_invalid_model_content_is_rejected(self):
        with serve(completion('{"title":"笔记","priority":"紧急"}'), content_type="application/json") as (config, _):
            with self.assertRaisesRegex(ChatError, "低、中、高"):
                extract_task(config, "整理笔记")

    def test_truncation_even_with_valid_json_is_rejected(self):
        body = completion('{"title":"笔记","priority":"中"}', "length")
        with serve(body, content_type="application/json") as (config, _):
            with self.assertRaisesRegex(ChatError, "未正常结束"):
                extract_task(config, "整理笔记")

    def test_refusal_is_rejected(self):
        with serve(completion(None, refusal="拒绝"), content_type="application/json") as (config, _):
            with self.assertRaisesRegex(ChatError, "模型拒绝"):
                extract_task(config, "整理笔记")

    def test_malformed_envelope(self):
        for body in ("not-json", '{}', '{"choices":[]}', '{"choices":[null]}', '{"error":{}}'):
            with self.subTest(body=body):
                with serve(body, content_type="application/json") as (config, _):
                    with self.assertRaises(ChatError):
                        extract_task(config, "整理笔记")

    def test_http_errors_do_not_expose_response(self):
        for status in (400, 401, 500):
            with self.subTest(status=status):
                with serve("private response", status=status) as (config, received):
                    with self.assertRaisesRegex(ChatError, f"HTTP {status}") as caught:
                        extract_task(config, "整理笔记")
                    self.assertNotIn("private response", str(caught.exception))
                    self.assertEqual(len(received), 1)

    def test_empty_description_sends_no_request(self):
        with serve("{}") as (config, received):
            with self.assertRaisesRegex(ChatError, "不能为空"):
                extract_task(config, " ")
            self.assertEqual(received, [])


if __name__ == "__main__":
    unittest.main()
