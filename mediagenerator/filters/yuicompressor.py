from django.conf import settings

from mediagenerator.generators.bundles.base import SubProcessFilter


class YUICompressor(SubProcessFilter):
    def __init__(self, **kwargs):
        # super(YUICompressor, self).__init__(**kwargs)
        super().__init__(**kwargs)
        assert self.filetype in {'css', 'js'}, (
            'YUICompressor only supports compilation to css and js. '
            'The parent filter expects "{}".'.format(self.filetype))

    def get_output(self, variation):
        for input in self.get_input(variation):
            try:
                compressor = settings.YUICOMPRESSOR_PATH
                yield self.run_process([
                    'java', '-jar', compressor, '--charset', 'utf-8', '--type', self.filetype
                ], input=input)
            except Exception as e:
                raise ValueError(
                    "Failed to execute Java VM or yuicompressor. "
                    "Please make sure that you have installed Java "
                    "and that it's in your PATH and that you've configured "
                    "YUICOMPRESSOR_PATH in your settings correctly.\n"
                    "Error was: {}".format(e)
                )
