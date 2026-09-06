import unittest
from pathlib import Path

from calibra_eval.environment import ComplianceEnvironment
from calibra_eval.io import load_tasks
from calibra_eval.ollama import OllamaAgent


class OllamaAgentParsingTests(unittest.TestCase):
    def test_native_tool_call_becomes_action(self):
        task = load_tasks(Path("benchmark/tasks"))[0]
        agent = OllamaAgent("fake")
        agent.client.chat_response = lambda *args, **kwargs: {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "verify_identity",
                            "arguments": {"party_id": "C-100", "verification_code": "alpha-100"},
                        }
                    }
                ],
            }
        }
        turn = agent.next_turn(task, ComplianceEnvironment(task), [])
        self.assertEqual(turn.action.tool, "verify_identity")
        self.assertEqual(turn.action.arguments["party_id"], "C-100")


if __name__ == "__main__":
    unittest.main()
