from rjsmin import jsmin

from mediagenerator.generators.bundles.base import Filter


class RJSMin(Filter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype == 'js', (
            f'RJSMin only supports compilation of JS (JavaScript). '
            f'The parent filter expects "{self.filetype}".')

    def get_output(self, variation):
        for source in self.get_input(variation):
            # TODO: keep_bang_comments=True ?
            yield jsmin(source)
