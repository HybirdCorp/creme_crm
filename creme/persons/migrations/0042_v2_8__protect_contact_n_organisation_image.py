from django.conf import settings
from django.db import migrations
from django.db.models.deletion import PROTECT

from creme.documents.models.fields import ImageEntityForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0041_v2_8__address_created_n_modified02'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='image',
            field=ImageEntityForeignKey(
                to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Photograph',
                blank=True, null=True, on_delete=PROTECT,
            ),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='image',
            field=ImageEntityForeignKey(
                to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Logo',
                blank=True, null=True, on_delete=PROTECT,
            ),
        ),
    ]
