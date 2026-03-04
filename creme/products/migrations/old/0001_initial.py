from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

from creme.documents.models.fields import ImageEntityManyToManyField


class Migration(migrations.Migration):
    # Memo: last migration was "0015_v2_6__fix_categories_uuids"
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the category')),
                ('description', models.CharField(max_length=100, verbose_name='Description', blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the sub-category')),
                ('description', models.CharField(max_length=100, verbose_name='Description', blank=True)),
                ('category', models.ForeignKey(verbose_name='Parent category', to='products.Category', on_delete=CASCADE)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Sub-category',
                'verbose_name_plural': 'Sub-categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('code', models.IntegerField(default=0, verbose_name='Code')),
                ('unit_price', models.DecimalField(verbose_name='Unit price', max_digits=8, decimal_places=2)),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('quantity_per_unit', models.IntegerField(null=True, verbose_name='Quantity/Unit', blank=True)),
                ('weight', models.DecimalField(null=True, verbose_name='Weight', max_digits=8, decimal_places=2, blank=True)),
                ('stock', models.IntegerField(null=True, verbose_name='Quantity/Stock', blank=True)),
                ('web_site', models.CharField(max_length=100, verbose_name='Web Site', blank=True)),
                ('category', models.ForeignKey(on_delete=PROTECT, verbose_name='Category', to='products.Category')),
                ('sub_category', models.ForeignKey(on_delete=PROTECT, verbose_name='Sub-category', to='products.SubCategory')),
                (
                    'images',
                    ImageEntityManyToManyField(
                        to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True,
                    )
                ),
            ],
            options={
                'swappable': 'PRODUCTS_PRODUCT_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Product',
                'verbose_name_plural': 'Products',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('reference', models.CharField(max_length=100, verbose_name='Reference')),
                ('countable', models.BooleanField(default=False, verbose_name='Countable')),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('quantity_per_unit', models.IntegerField(null=True, verbose_name='Quantity/Unit', blank=True)),
                ('unit_price', models.DecimalField(verbose_name='Unit price', max_digits=8, decimal_places=2)),
                ('web_site', models.CharField(max_length=100, verbose_name='Web Site', blank=True)),
                ('category', models.ForeignKey(on_delete=PROTECT, verbose_name='Category', to='products.Category')),
                ('sub_category', models.ForeignKey(on_delete=PROTECT, verbose_name='Sub-category', to='products.SubCategory')),
                (
                    'images',
                    ImageEntityManyToManyField(
                        to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True,
                    )
                ),
            ],
            options={
                'swappable': 'PRODUCTS_SERVICE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Service',
                'verbose_name_plural': 'Services',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
