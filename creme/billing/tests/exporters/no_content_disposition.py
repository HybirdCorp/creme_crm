from django.http import HttpResponse
from django.views.generic.base import ContextMixin

from creme.billing.exporters import base


class NoContentDispositionExporter(ContextMixin, base.BillingExporter):
    def __init__(self, **kwargs):
        super().__init__(**{
            'verbose_name': 'Test (no content disposition)',
            **kwargs,
        })

    def export(self, entity, user):
        return HttpResponse(
            content=f'name={entity.name}'.encode(),
            headers={
                'Content-Type': 'application/ini',
                # 'Content-Disposition': 'attachment; filename="..."',  # <==
            },
        )


class NoContentDispositionExportEngine(base.BillingExportEngine):
    id = base.BillingExportEngine.generate_id('billing', 'no_content_disp')

    @property
    def flavours(self):
        yield base.ExporterFlavour.agnostic()

    def exporter(self, flavour):
        return NoContentDispositionExporter(engine=self, flavour=flavour)
