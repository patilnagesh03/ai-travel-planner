"""
Unit tests for the Ollama HTTP client.

Every test mocks `requests`, so the suite never needs a running Ollama
server.
"""

import json
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from backend.apps.ai.clients import OllamaClient, parse_json_completion
from backend.apps.ai.exceptions import (
    AIModelError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIResponseError,
)


POST_TARGET = "backend.apps.ai.clients.ollama_client.requests.post"
GET_TARGET = "backend.apps.ai.clients.ollama_client.requests.get"


def build_response(status_code=200, payload=None, headers=None):
    response = Mock()

    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers if headers is not None else {}
    response.json.return_value = payload

    return response


class OllamaClientTests(SimpleTestCase):

    def setUp(self):
        self.client = OllamaClient()

    def test_generate_returns_the_raw_completion(self):
        payload = {
            "model": "llama3.1",
            "response": '{"title": "Bengaluru Trip"}',
            "done": True,
        }

        with patch(
            POST_TARGET,
            return_value=build_response(payload=payload),
        ):
            completion = self.client.generate(prompt="Plan a trip.")

        self.assertEqual(
            completion,
            '{"title": "Bengaluru Trip"}',
        )

    def test_request_asks_for_json_and_uses_the_configured_model(self):
        payload = {"response": "{}", "done": True}

        with patch(
            POST_TARGET,
            return_value=build_response(payload=payload),
        ) as mocked_post:
            self.client.generate(
                prompt="Plan a trip.",
                system="You are a planner.",
            )

        kwargs = mocked_post.call_args.kwargs

        self.assertEqual(kwargs["json"]["model"], self.client.model)
        self.assertEqual(kwargs["json"]["format"], "json")
        self.assertFalse(kwargs["json"]["stream"])
        self.assertEqual(kwargs["json"]["prompt"], "Plan a trip.")
        self.assertEqual(
            kwargs["json"]["system"],
            "You are a planner.",
        )
        self.assertEqual(kwargs["timeout"], self.client.timeout)

    def test_system_prompt_is_optional(self):
        payload = {"response": "{}", "done": True}

        with patch(
            POST_TARGET,
            return_value=build_response(payload=payload),
        ) as mocked_post:
            self.client.generate(prompt="Plan a trip.")

        self.assertNotIn("system", mocked_post.call_args.kwargs["json"])

    def test_missing_response_field_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"done": True}),
        ):
            with self.assertRaises(AIResponseError):
                self.client.generate(prompt="Plan a trip.")

    def test_non_string_response_raises_response_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(payload={"response": 42}),
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

    def test_missing_model_raises_model_error(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=404),
        ):
            with self.assertRaises(AIModelError):
                self.client.generate(prompt="Plan a trip.")

    def test_server_error_raises_unavailable(self):
        with patch(
            POST_TARGET,
            return_value=build_response(status_code=500),
        ):
            with self.assertRaises(AIProviderUnavailableError):
                self.client.generate(prompt="Plan a trip.")

    def test_list_models_returns_model_names(self):
        payload = {
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "mistral:latest"},
            ],
        }

        with patch(
            GET_TARGET,
            return_value=build_response(payload=payload),
        ):
            models = self.client.list_models()

        self.assertEqual(
            models,
            ["llama3.1:latest", "mistral:latest"],
        )

    def test_is_available_reports_false_when_the_server_is_down(self):
        with patch(
            GET_TARGET,
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            self.assertFalse(self.client.is_available())

    def test_is_available_reports_true_when_the_model_is_present(self):
        payload = {"models": [{"name": self.client.model}]}

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
            parse_json_completion("[1, 2, 3]")

    def test_a_non_string_raises_response_error(self):
        with self.assertRaises(AIResponseError):
            parse_json_completion(None)
