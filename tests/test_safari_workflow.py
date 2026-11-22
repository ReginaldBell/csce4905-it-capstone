import unittest
from pathlib import Path


class SafariWorkflowTests(unittest.TestCase):
    def test_simulator_inventory_allows_for_runner_setup(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text()

        self.assertIn('def output(*command, timeout=60):', workflow)
        self.assertIn('subprocess.check_output(command, text=True, timeout=timeout)', workflow)
        self.assertIn('output("xcrun", "simctl", "list", "--json", timeout=180)', workflow)
