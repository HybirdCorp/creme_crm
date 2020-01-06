from django.template import Context, Template as DjangoTemplate

from mediagenerator.generators.bundles.base import Filter


class Template(Filter):
    def get_output(self, variation):
        for input in self.get_input(variation):
            yield self._template(input)

    def get_dev_output(self, name, variation):
        content = super().get_dev_output(name, variation)
        return self._template(content)

    def _template(self, content):
        context = Context({})
        context.autoescape = self.filetype == 'html'

        return DjangoTemplate(content).render(context)
