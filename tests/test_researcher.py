import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sqlite3
from src.researcher import Researcher
from src.models import AnimalSensoryData

class TestResearcher(unittest.TestCase):
    def setUp(self):
        # Setup mock DB and directory
        self.test_db = 'test_orchestrator.db'
        self.test_vault = 'test_vault'
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if not os.path.exists(self.test_vault):
            os.makedirs(self.test_vault)

        # Patch DB path and Vault dir in researcher module
        self.db_patcher = patch('src.researcher.DB_PATH', self.test_db)
        self.vault_patcher = patch('src.researcher.VAULT_DIR', self.test_vault)
        self.db_patcher.start()
        self.vault_patcher.start()

        # Init DB
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS research_queue (
                id INTEGER PRIMARY KEY,
                animal_name TEXT UNIQUE,
                taxonomy_source TEXT,
                priority INTEGER,
                status TEXT DEFAULT 'PENDING',
                attempts INTEGER DEFAULT 0
            )
        ''')
        # Add a job
        c.execute("INSERT INTO research_queue (animal_name, priority) VALUES (?, ?)", ("Test Dolphin", 1))
        conn.commit()
        conn.close()

    def tearDown(self):
        self.db_patcher.stop()
        self.vault_patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_vault):
            import shutil
            shutil.rmtree(self.test_vault)

    @patch('src.researcher.ollama.chat')
    def test_researcher_run(self, mock_chat):
        # Mock LLM response with valid JSON matching Schema v4.0
        mock_response_content = json.dumps({
            "identity": {
                "common_name": "Test Dolphin",
                "scientific_name": "Tursiops truncatus",
                "taxonomy": {
                    "class": "Mammalia",
                    "order": "Artiodactyla"
                }
            },
            "sensory_modalities": [
                {
                    "modality_domain": "Mechanoreception",
                    "sub_type": "Echolocation",
                    "stimulus_type": "Acoustic Pressure Wave",
                    "quantitative_data": {
                        "min": 1000,
                        "max": 150000,
                        "unit": "Hz",
                        "context": "Bio-sonar"
                    },
                    "mechanism": {
                        "level": "Anatomical",
                        "description": "Melon and Cochlea"
                    },
                    "evidence": [
                        {
                            "source_type": "Experiment",
                            "citation": "Test et al. 2024"
                        }
                    ]
                }
            ],
            "meta": {
                "data_quality_flag": "High_Evidence"
            }
        })

        mock_chat.return_value = {'message': {'content': mock_response_content}}

        agent = Researcher()
        agent.run()

        # Verify job status updated to COMPLETED
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        status = c.execute("SELECT status FROM research_queue WHERE animal_name='Test Dolphin'").fetchone()[0]
        conn.close()
        self.assertEqual(status, "COMPLETED")

        # Verify JSON file created
        files = os.listdir(self.test_vault)
        self.assertIn("Test_Dolphin.json", files)

        # Verify content
        with open(os.path.join(self.test_vault, "Test_Dolphin.json"), 'r') as f:
            data = json.load(f)
            self.assertEqual(data['identity']['common_name'], "Test Dolphin")

    @patch('src.researcher.ollama.chat')
    def test_validation_failure(self, mock_chat):
        # Mock LLM response with INVALID JSON (missing required field)
        mock_response_content = json.dumps({
            "identity": {
                "common_name": "Bad Dolphin"
                # Missing scientific_name, taxonomy, etc.
            },
            "sensory_modalities": [],
            "meta": {"data_quality_flag": "Low_Data"}
        })

        mock_chat.return_value = {'message': {'content': mock_response_content}}

        # Add bad job
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("INSERT INTO research_queue (animal_name, priority) VALUES (?, ?)", ("Bad Dolphin", 1))
        conn.commit()
        conn.close()

        agent = Researcher()
        # We need to ensure we pick the bad job. The get_job fetches LIMIT 1.
        # Since Test Dolphin is COMPLETED (if we ran previous test? No, new setUp),
        # but wait, setUp creates Test Dolphin.
        # I should clear queue or update Test Dolphin to COMPLETED first.
        # But this is a separate test method, setUp runs again.
        # So I have Test Dolphin (id 1) and Bad Dolphin (id 2).
        # get_job orders by priority. Both 1. ID 1 comes first.
        # I will just update Test Dolphin to COMPLETED manually.
        conn = sqlite3.connect(self.test_db)
        conn.execute("UPDATE research_queue SET status='COMPLETED' WHERE animal_name='Test Dolphin'")
        conn.commit()
        conn.close()

        agent.run()

        # Verify job status updated to FAILED
        conn = sqlite3.connect(self.test_db)
        status = conn.execute("SELECT status FROM research_queue WHERE animal_name='Bad Dolphin'").fetchone()[0]
        conn.close()
        self.assertEqual(status, "FAILED")

if __name__ == '__main__':
    unittest.main()
