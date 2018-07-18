from django.conf import settings
from django.utils.encoding import smart_str

from mediagenerator.generators.bundles.base import Filter


class YUICompressor(Filter):
    def __init__(self, **kwargs):
        # super(YUICompressor, self).__init__(**kwargs)
        super().__init__(**kwargs)
        assert self.filetype in {'css', 'js'}, (
            'YUICompressor only supports compilation to css and js. '
            'The parent filter expects "{}".'.format(self.filetype))

    def get_output(self, variation):
        # We import this here, so App Engine Helper users don't get import errors.
        from subprocess import Popen, PIPE

        for input in self.get_input(variation):
            try:
                compressor = settings.YUICOMPRESSOR_PATH
                cmd = Popen(['java', '-jar', compressor,
                             '--charset', 'utf-8', '--type', self.filetype],
                            stdin=PIPE, stdout=PIPE, stderr=PIPE,
                            universal_newlines=True)
                output, error = cmd.communicate(smart_str(input))

                assert cmd.wait() == 0, 'Command returned bad result:\n{}'.format(error)

                # yield output.decode('utf-8')
                yield output
            except Exception as e:
                raise ValueError(
                    "Failed to execute Java VM or yuicompressor. "
                    "Please make sure that you have installed Java "
                    "and that it's in your PATH and that you've configured "
                    "YUICOMPRESSOR_PATH in your settings correctly.\n"
                    "Error was: {}".format(e)
                )
