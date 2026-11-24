import unittest
from project import demo


class ContractTests(unittest.TestCase):
    def test_live_response_contract_checks_catch_and_verify_repair(self):
        output = demo()
        self.assertTrue(output["v1"]["accept"])
        self.assertTrue(output["compatible"]["accept"])
        self.assertFalse(output["breaking"]["accept"])
        contracts = output["breaking"]["contracts"]
        self.assertEqual(contracts["finance export"]["violations"][0]["rule"], "required")
        self.assertEqual(contracts["operations portal"]["violations"][0]["path"], "stage")
        self.assertTrue(all(row["invalid_request_http"] == 422 for row in output.values()))
