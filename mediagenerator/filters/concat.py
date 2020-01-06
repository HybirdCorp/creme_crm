from hashlib import sha1

from django.utils.encoding import smart_str

from mediagenerator.generators.bundles.base import Filter


class Concat(Filter):
    """
    Simply concatenates multiple files into a single file.

    This is also the default root filter.
    """
    def __init__(self, **kwargs):
        self.config(kwargs, concat_dev_output=False, dev_output_name='concat')
        super().__init__(**kwargs)

    def get_output(self, variation):
        yield '\n\n'.join(input for input in self.get_input(variation))

    def get_dev_output(self, name, variation):
        if not self.concat_dev_output:
            return super().get_dev_output(name, variation)

        assert self.dev_output_name == name

        names = super().get_dev_output_names(variation)

        return '\n\n'.join(super().get_dev_output(name[0], variation)
                           for name in names)

    def get_dev_output_names(self, variation):
        if not self.concat_dev_output:
            for data in super().get_dev_output_names(variation):
                yield data

            return

        content = self.get_dev_output(self.dev_output_name, variation)

        yield self.dev_output_name, sha1(smart_str(content)).hexdigest()
