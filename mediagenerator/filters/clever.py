from mediagenerator.generators.bundles.base import Filter

from clevercss import convert


class CleverCSS(Filter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype == 'css', (
            f'CleverCSS only supports compilation to css. '
            f'The parent filter expects "{self.filetype}".')
        self.input_filetype = 'clevercss'

    def should_use_default_filter(self, ext):
        return False if ext == 'ccss' else super().should_use_default_filter(ext)

    def get_output(self, variation):
        for input in self.get_input(variation):
            yield convert(input)

    def get_dev_output(self, name, variation):
        content = super().get_dev_output(name, variation)
        return convert(content)
