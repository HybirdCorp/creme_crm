from csscompressor import compress

from mediagenerator.generators.bundles.base import Filter


class CSSCompressor(Filter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype == 'css', (
            f'CSSCompressor only supports compilation of CSS. '
            f'The parent filter expects "{self.filetype}".')

    def get_output(self, variation):
        for source in self.get_input(variation):
            yield compress(source)
