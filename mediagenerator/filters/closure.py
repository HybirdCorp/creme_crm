import json

from django.conf import settings

from mediagenerator.generators.bundles.base import SubProcessFilter

COMPILATION_LEVEL = getattr(
    settings, 'CLOSURE_COMPILATION_LEVEL', 'SIMPLE_OPTIMIZATIONS'
)


class Closure(SubProcessFilter):
    def __init__(self, **kwargs):
        self.config(kwargs, compilation_level=COMPILATION_LEVEL)
        super().__init__(**kwargs)
        assert self.filetype == 'js', (
            f'Closure only supports compilation to js. '
            f'The parent filter expects "{self.filetype}".')

    def parse_errors(self, output):
        try:
            # ignore the first line which is not json (WTF !)
            errors = json.loads(output.splitlines()[1])
        except json.decoder.JSONDecodeError:
            return []

        return [
            (e['line'], e['column'], e['description'])
            for e in errors if e['level'] == 'error'
        ]

    def get_output(self, variation):
        # We import this here, so App Engine Helper users don't get import
        # errors.
        compressor = settings.CLOSURE_COMPILER_PATH

        for source in self.get_input(variation):
            try:
                yield self.run_process([
                    'java', '-jar', compressor,
                    '--charset', 'utf-8',
                    '--compilation_level', self.compilation_level,
                    '--error_format', 'JSON'
                ], input=source)
            except SubProcessFilter.ProcessError as e:
                errors = self.parse_errors(e.stderr)

                if errors:
                    message = self.format_lint_errors(errors, source)
                else:
                    message = f"The Closure compiler has returned an error. {e.stderr}"

                raise ValueError(message) from e

            except Exception as e:
                raise ValueError(
                    "Failed to execute Java VM or Closure. "
                    "Please make sure that you have installed Java "
                    "and that it's in your PATH and that you've configured "
                    "CLOSURE_COMPILER_PATH in your settings correctly.\n"
                    f"Error was: {e}"
                )
