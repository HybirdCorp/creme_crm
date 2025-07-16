import re
import unittest
from collections import defaultdict
from pathlib import Path

from django.conf import settings


class TestUUIDs(unittest.TestCase):
    """Test to identify duplicate UUIDs that could be extracted as constants."""

    uuid_pattern = re.compile(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        re.IGNORECASE
    )

    def iter_project_files(self):
        """Iterate over all Python files in the project."""

        project_root = Path(settings.CREME_ROOT).resolve()
        for python_file in project_root.rglob('*.py'):
            if 'migrations' in str(python_file):
                continue
            yield python_file

    def test_find_duplicate_uuids(self):
        """Search for duplicate UUIDs in project files."""

        uuid_occurrences = defaultdict(list)

        for python_file in self.iter_project_files():
            with open(python_file, 'r', encoding='utf-8') as f:
                content = f.read()

            uuids = self.uuid_pattern.finditer(content)
            for match in uuids:
                uuid = match.group()
                uuid_occurrences[uuid].append(str(python_file))

        duplicate_uuids = {
            uuid: files
            for uuid, files in uuid_occurrences.items()
            if len(files) > 1
        }

        if duplicate_uuids:
            message = "Duplicate UUIDs found:\n\n"
            for uuid, files in duplicate_uuids.items():
                message += f"UUID: {uuid}\nFound in files:\n"
                for file in files:
                    message += f"  - {file}\n"
                message += "\n"

            self.fail(message)
