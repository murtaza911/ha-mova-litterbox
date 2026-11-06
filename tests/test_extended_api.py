"""Focused cloud-command tests that do not contact MOVA or move the device."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

PACKAGE = types.ModuleType("mova_best_test")
PACKAGE.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "mova_litterbox")]
sys.modules[PACKAGE.__name__] = PACKAGE
api = importlib.import_module("mova_best_test.api")


class MovaCloudCommandsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = api.MovaApiClient(None, "example@example.com", "secret", "CA", "us")
        self.client.did = "123"

    async def test_property_reads_are_batched_and_ignore_failed_items(self):
        async def post(endpoint, body):
            params = body["data"]["params"]
            self.assertLessEqual(len(params), 20)
            return {"data": {"result": [
                {**item, "code": -4003 if item["piid"] == 21 else 0, "value": item["piid"]}
                for item in params
            ]}}

        self.client._post = AsyncMock(side_effect=post)
        result = await self.client.get_properties([(3, i) for i in range(1, 22)])
        self.assertEqual(2, self.client._post.await_count)
        self.assertEqual(1, result[(3, 1)])
        self.assertNotIn((3, 21), result)

    async def test_action_payload_and_cloud_error(self):
        self.client._post = AsyncMock(return_value={"data": {"result": {"code": 0}}})
        await self.client.call_action(3, 5)
        body = self.client._post.await_args.args[1]
        self.assertEqual("action", body["data"]["method"])
        self.assertEqual({"did": "123", "siid": 3, "aiid": 5, "in": []}, body["data"]["params"])

        self.client._post = AsyncMock(return_value={"data": {"result": {"code": -4003}}})
        with self.assertRaises(api.MovaApiError):
            await self.client.call_action(3, 5)


if __name__ == "__main__":
    unittest.main()
