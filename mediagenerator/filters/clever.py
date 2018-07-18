from mediagenerator.generators.bundles.base import Filter

from clevercss import convert


class CleverCSS(Filter):
    def __init__(self, **kwargs):
        # super(CleverCSS, self).__init__(**kwargs)
        super().__init__(**kwargs)
        assert self.filetype == 'css', (
            'CleverCSS only supports compilation to css. '
            'The parent filter expects "{}".'.format(self.filetype))
        self.input_filetype = 'clevercss'

    def should_use_default_filter(self, ext):
        # if ext == 'ccss':
        #     return False
        # return super(CleverCSS, self).should_use_default_filter(ext)
        return False if ext == 'ccss' else super().should_use_default_filter(ext)

    def get_output(self, variation):
        for input in self.get_input(variation):
            yield convert(input)

    def get_dev_output(self, name, variation):
        # content = super(CleverCSS, self).get_dev_output(name, variation)
        content = super().get_dev_output(name, variation)
        return convert(content)
