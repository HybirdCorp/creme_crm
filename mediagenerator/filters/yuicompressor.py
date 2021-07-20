import re

from django.conf import settings

from mediagenerator.generators.bundles.base import SubProcessFilter


class YUICompressor(SubProcessFilter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype in {'css', 'js'}, (
            f'YUICompressor only supports compilation of CSS and JS files. '
            f'The parent filter expects "{self.filetype}".')

    def parse_errors(self, e):
        pattern = re.compile(
            r'^\[ERROR\]\s+(?P<line>[0-9]+):(?P<col>[0-9]+):(?P<message>.+)\n',
            re.MULTILINE
        )
        errors = pattern.findall(str(e))

        # The last error is the java exception raised by compressor, so ignore it
        return [
            (int(index), int(col), message) for index, col, message in errors[:-1]
        ]

    def get_output(self, variation):
        for source in self.get_input(variation):
            try:
                compressor = settings.YUICOMPRESSOR_PATH
                yield self.run_process([
                    'java', '-jar', compressor,
                    '--charset', 'utf-8',
                    '--type', self.filetype
                ], input=source)
            except SubProcessFilter.ProcessError as e:
                errors = self.parse_errors(e.stderr)

                if errors:
                    message = self.format_lint_errors(errors, source)
                else:
                    f"The YUI Compressor has returned an error. {e.stderr}"

                raise ValueError(message)
            except Exception as e:
                raise ValueError(
                    "Failed to execute Java VM or yuicompressor. "
                    "Please make sure that you have installed Java "
                    "and that it's in your PATH and that you've configured "
                    "YUICOMPRESSOR_PATH in your settings correctly.\n"
                    "{}".format(e)
                )
