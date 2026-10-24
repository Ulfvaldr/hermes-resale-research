import json
import os
import unittest
from unittest.mock import patch

from hermes_resale_research.n8n_client import post_evaluation, webhook_url


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class N8nClientTests(unittest.TestCase):
    def test_posts_contract_without_business_logic(self):
        with patch("hermes_resale_research.n8n_client.urlopen", return_value=_Response(b'{"recommendation":"WATCH"}')) as opened:
            result = post_evaluation({"evaluation": {"id": "fixture-1"}}, url="http://n8n.test/hook")
        request = opened.call_args.args[0]
        self.assertTrue(result.ok)
        self.assertEqual(result.as_dict()["data"], {"recommendation": "WATCH"})
        self.assertEqual(json.loads(request.data), {"evaluation": {"id": "fixture-1"}})
        self.assertEqual(request.get_header("Content-type"), "application/json")

    def test_connection_and_malformed_response_fail_closed(self):
        with patch("hermes_resale_research.n8n_client.urlopen", side_effect=OSError):
            self.assertEqual(post_evaluation({}).error["code"], "CONNECTION_ERROR")
        with patch("hermes_resale_research.n8n_client.urlopen", return_value=_Response(b"not-json")):
            self.assertEqual(post_evaluation({}).error["code"], "MALFORMED_RESPONSE")

    def test_endpoint_is_configurable(self):
        with patch.dict(os.environ, {"N8N_RESALE_WEBHOOK_URL": "http://custom/hook"}):
            self.assertEqual(webhook_url(), "http://custom/hook")


if __name__ == "__main__":
    unittest.main()
