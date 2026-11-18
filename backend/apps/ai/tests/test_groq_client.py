"""
Unit tests for the Groq HTTP client.

Every test mocks `requests`, so the suite never needs a real API key and
never makes a network call.
"""

import json
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from backend.apps.ai.clients import GroqClient, parse_json_completion
from backend.apps.ai.exceptions import (
    AIModelError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseError,
)


POST_TARGET = "backend.apps.ai.clients.groq_client.requests.post"
GET_TARGET = "backend.apps.ai.clients.groq_client.requests.get"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


def chat_payload(content='{"title": "Bengaluru Trip"}'):
    return {
        "id": "chatcmpl-1",
        "model": "openai/gpt-oss-120b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            },
        ],
    }


class GroqClientTests(SimpleTestCase):

    def setUp(self):
        self.client = GroqClient(api_key="test-key")

    def test_generate_returns_the_raw_completion(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=chat_payload()),
        ):
            completion = self.client.generate(prompt="Plan a trip.")

        self.assertEqual(
            completion,
            '{"title": "Bengaluru Trip"}',
        )

    def test_request_asks_for_json_and_uses_the_configured_model(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=chat_payload("{}")),
        ) as mocked_post:
            self.client.generate(
                prompt="Plan a trip.",
                system="You are a planner.",
            )

        kwargs = mocked_post.call_args.kwargs

        self.assertEqual(kwargs["json"]["model"], self.client.model)
        self.assertEqual(
            kwargs["json"]["response_format"],
            {"type": "json_object"},
        )
        self.assertFalse(kwargs["json"]["stream"])
        self.assertEqual(
            kwargs["json"]["temperature"],
            self.client.temperature,
        )
        self.assertGreater(
            kwargs["json"]["max_completion_tokens"],
            0,
        )
        self.assertEqual(
            kwargs["json"]["messages"],
            [
                {"role": "system", "content": "You are a planner."},
                {"role": "user", "content": "Plan a trip."},
            ],
        )
        self.assertEqual(kwargs["timeout"], self.client.timeout)

    def test_system_prompt_is_optional(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=chat_payload("{}")),
        ) as mocked_post:
            self.client.generate(prompt="Plan a trip.")

        messages = mocked_post.call_args.kwargs["json"]["messages"]

        self.assertEqual(
            messages,
            [{"role": "user", "content": "Plan a trip."}],
        )

    def test_the_api_key_is_sent_as_a_bearer_token(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=chat_payload("{}")),
        ) as mocked_post:
            self.client.generate(prompt="Plan a trip.")

        headers = mocked_post.call_args.kwargs["headers"]

        self.assertEqual(
            headers["Authorization"],
            "Bearer test-key",
        )

    def test_a_missing_api_key_raises_model_error_before_the_call(self):
        client = GroqClient(api_key="")

        with patch(POST_TARGET) as mocked_post:
            with self.assertRaises(AIModelError):
                client.generate(prompt="Plan a trip.")

        mocked_post.assert_not_called()

    def test_missing_choices_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"id": "x"}),
        ):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_empty_choices_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"choices": []}),
        ):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_missing_content_raises_response_error(self):
        payload = {
            "choices": [{"message": {"role": "assistant"}}],
        }

        with patch(
            POST_TARGET,
            return_value=build_response(payload=payload),
        ):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_blank_content_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload=chat_payload("   ")),
        ):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_invalid_json_raises_response_error(self):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.headers = {}
        response.json.side_effect = ValueError("not json")

        with patch(POST_TARGET, return_value=response):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_connection_error_raises_unavailable(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with self.assertRaises(AIProviderUnavailableError):
                self.client.generate(prompt="Plan a trip.")

    def test_timeout_raises_timeout_error(self):
        with patch(
            POST_TARGET,
            side_effect=requests.exceptions.ReadTimeout("timed out"),
        ):
            with self.assertRaises(AIProviderTimeoutError):
                self.client.generate(prompt="Plan a trip.")

    def test_rejected_api_key_raises_model_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=401),
        ):
            with self.assertRaises(AIModelError):
                self.client.generate(prompt="Plan a trip.")

    def test_unknown_model_raises_model_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=404),
        ):
            with self.assertRaises(AIModelError):
                self.client.generate(prompt="Plan a trip.")

    def test_rate_limit_raises_unavailable(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=429),
        ):
            with self.assertRaises(AIProviderUnavailableError):
                self.client.generate(prompt="Plan a trip.")

    def test_server_error_raises_unavailable(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=500),
        ):
            with self.assertRaises(AIProviderUnavailableError):
                self.client.generate(prompt="Plan a trip.")

    def test_list_models_returns_model_ids(self):
        payload = {
            "data": [
                {"id": "openai/gpt-oss-120b"},
                {"id": "openai/gpt-oss-20b"},
            ],
        }

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            models = self.client.list_models()

        self.assertEqual(
            models,
            ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        )

    def test_is_available_reports_false_without_a_key(self):
        client = GroqClient(api_key="")

        with patch(GET_TARGET) as mocked_get:
            self.assertFalse(client.is_available())

        mocked_get.assert_not_called()

    def test_is_available_reports_false_when_the_api_is_down(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            self.assertFalse(self.client.is_available())

    def test_is_available_reports_true_when_the_model_is_listed(self):
        payload = {"data": [{"id": self.client.model}]}

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            self.assertTrue(self.client.is_available())


class ParseJsonCompletionTests(SimpleTestCase):

    def test_plain_json_is_parsed(self):
        payload = parse_json_completion('{"title": "Trip"}')

        self.assertEqual(payload["title"], "Trip")

    def test_markdown_fenced_json_is_parsed(self):
        completion = (
            "```json\n"
            '{"title": "Trip"}\n'
            "```"
        )

        payload = parse_json_completion(completion)

        self.assertEqual(payload["title"], "Trip")

    def test_unfenced_markdown_json_is_parsed(self):
        completion = (
            "```\n"
            '{"title": "Trip"}\n'
            "```"
        )

        payload = parse_json_completion(completion)

        self.assertEqual(payload["title"], "Trip")

    def test_invalid_json_raises_response_error(self):
        with self.assertRaises(AIResponseError):
            parse_json_completion("this is not json")

    def test_a_json_array_raises_response_error(self):
        with self.assertRaises(AIResponseError):
            parse_json_completion(json.dumps([1, 2, 3]))

    def test_a_non_string_raises_response_error(self):
        with self.assertRaises(AIResponseError):
            parse_json_completion(None)
