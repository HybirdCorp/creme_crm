import os
import pathlib

from creme.creme_core.utils.test import CremeDiscoverRunner


class PyTestDiscoverRunner(CremeDiscoverRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def pytest_to_django_label(self, label):
        path, _sep, raw_patterns = label.partition('::')
        path = pathlib.Path(path).absolute()
        patterns = raw_patterns.split('::') if raw_patterns else ()

        if path.exists() and path.suffix == '.py':
            modules = [p.name for p in path.relative_to(os.getcwd()).parents if p.name]
            modules.reverse()
            modules.append(path.name.replace(path.suffix, ''))

            label = '.'.join(modules)

            if patterns:
                self.test_name_patterns = {
                    *(self.test_name_patterns or {}),
                    f'{label}.*{".".join(patterns)}*'
                }

        return label

    def build_suite(self, test_labels, extra_tests):
        test_labels = [self.pytest_to_django_label(label) for label in test_labels]
        return super().build_suite(test_labels, extra_tests)
