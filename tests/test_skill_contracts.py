import json
from pathlib import Path
import unittest
import app.main
from app.assistant import RunInput,Selection,SKILLS


class SkillContracts(unittest.TestCase):
    def test_packages_match_executable_contract(self):
        for name in SKILLS:
            root=Path('skills')/name
            schema=json.loads((root/'schema.json').read_text())
            self.assertEqual(schema['input'],RunInput.model_json_schema())
            self.assertEqual(schema['model_output'],Selection.model_json_schema())
            self.assertEqual(json.loads((root/'binding.json').read_text())['handler'],'app.assistant.run_skill')
            self.assertTrue((root/'SKILL.md').is_file())
