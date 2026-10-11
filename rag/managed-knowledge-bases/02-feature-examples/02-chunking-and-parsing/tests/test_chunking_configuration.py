"""Offline checks of the notebook's actual embedding and constructor configuration."""

import ast
import contextlib
import io
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


DIRECTORY = Path(__file__).resolve().parents[1]
NOTEBOOK = DIRECTORY / "01-chunking-strategies.ipynb"


class ChunkingConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.cells = json.loads(NOTEBOOK.read_text())["cells"]
        assignments = [
            node for cell in self.cells if cell["cell_type"] == "code"
            for node in ast.parse("".join(cell["source"]).replace("%pip", "# %pip")).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "embedding_model"
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        self.embedding_model = ast.literal_eval(assignments[0].value)

    def test_shared_embedding_is_explicit_and_supported(self):
        self.assertEqual(self.embedding_model, "amazon.titan-embed-text-v2:0")
        utility = DIRECTORY.parents[1] / "utils" / "managed_knowledge_base.py"
        supported = next(
            ast.literal_eval(node.value) for node in ast.parse(utility.read_text()).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "VALID_EMBEDDING_MODELS"
                    for target in node.targets)
        )
        self.assertIn(self.embedding_model, supported)

    def test_both_constructor_cells_share_embedding_and_preserve_chunking(self):
        constructor = Mock()
        module = ModuleType("utils.managed_knowledge_base")
        module.ManagedKnowledgeBase = constructor
        namespace = {
            "embedding_model": self.embedding_model, "bucket_name": "test-bucket",
            "suffix": "test", "region": "us-east-1", "time": Mock(),
        }
        cells = [cell for cell in self.cells if cell["cell_type"] == "code"
                 and "= ManagedKnowledgeBase(" in "".join(cell["source"])]
        self.assertEqual(len(cells), 2)
        with patch.dict(sys.modules, {"utils.managed_knowledge_base": module}), \
                contextlib.redirect_stdout(io.StringIO()):
            for cell in cells:
                # Only execute constructor cells from this fixed, checked-in notebook.
                exec(  # nosec B102  # noqa: S102
                    compile("".join(cell["source"]), str(NOTEBOOK), "exec"), namespace,
                )
        self.assertEqual(constructor.call_count, 2)
        default, fixed = [call.kwargs for call in constructor.call_args_list]
        for config in (default, fixed):
            self.assertEqual(config["embedding_model"], self.embedding_model)
        self.assertEqual(default["bucket_name"], "test-bucket")
        self.assertNotIn("data_sources", default)
        self.assertEqual(fixed["data_sources"], [{
            "type": "S3", "bucket_name": "test-bucket", "chunking_strategy": "FIXED_SIZE",
            "max_tokens": 500, "overlap_percentage": 20,
        }])
        self.assertEqual(constructor.return_value.start_ingestion_job.call_count, 2)


if __name__ == "__main__":
    unittest.main()
