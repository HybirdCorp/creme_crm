# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import SET_NULL, CASCADE

from creme.creme_core.models import fields as creme_fields

from creme.documents.models.fields import ImageEntityForeignKey


class Migration(migrations.Migration):
    # replaces = [
    #     (b'persons', '0001_initial'),
    #     (b'persons', '0008_v1_7__charfields_not_nullable_1'),
    #     (b'persons', '0009_v1_7__charfields_not_nullable_2'),
    #     (b'persons', '0010_v1_7__lv_indexes'),
    #     (b'persons', '0011_v1_7__fax_not_nullable_1'),
    #     (b'persons', '0012_v1_7__fax_not_nullable_2'),
    #     (b'persons', '0013_v1_7__image_to_doc_1'),
    #     (b'persons', '0014_v1_7__image_to_doc_2'),
    #     (b'persons', '0015_v1_7__image_to_doc_3'),
    #     (b'persons', '0016_v1_7__image_to_doc_4'),
    #     (b'persons', '0017_v1_7__organisation_managed_1'),
    #     (b'persons', '0018_v1_7__organisation_managed_2'),
    #     (b'persons', '0019_v1_7__first_persons_uuids'),
    # ]

    initial = True
    dependencies = [
        ('contenttypes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
        # ('media_managers', '0001_initial'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Civility',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('shortcut', models.CharField(max_length=100, verbose_name='Shortcut')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Civility',
                'verbose_name_plural': 'Civilities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LegalForm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Legal form',
                'verbose_name_plural': 'Legal forms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'People position',
                'verbose_name_plural': 'People positions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sector',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Line of business',
                'verbose_name_plural': 'Lines of business',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StaffSize',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('size', models.CharField(max_length=100, verbose_name='Size')),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Organisation staff size',
                'verbose_name_plural': 'Organisation staff sizes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name', blank=True)),
                ('address', models.TextField(verbose_name='Address', blank=True)),
                ('po_box', models.CharField(max_length=50, verbose_name='PO box', blank=True)),
                ('zipcode', models.CharField(max_length=100, verbose_name='Zip code', blank=True)),
                ('city', models.CharField(max_length=100, verbose_name='City', blank=True)),
                ('department', models.CharField(max_length=100, verbose_name='Department', blank=True)),
                ('state', models.CharField(max_length=100, verbose_name='State', blank=True)),
                ('country', models.CharField(max_length=40, verbose_name='Country', blank=True)),
                ('object_id', models.PositiveIntegerField(editable=False)),
                ('content_type', models.ForeignKey(related_name='object_set', editable=False, to='contenttypes.ContentType', on_delete=CASCADE)),
            ],
            options={
                'ordering': ('id',),
                'swappable': 'PERSONS_ADDRESS_MODEL',
                'verbose_name': 'Address',
                'verbose_name_plural': 'Addresses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('civility', models.ForeignKey(on_delete=SET_NULL, verbose_name='Civility', blank=True, to='persons.Civility', null=True)),
                ('last_name', models.CharField(max_length=100, verbose_name='Last name')),
                ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('phone', creme_fields.PhoneField(max_length=100, verbose_name='Phone number', blank=True)),
                ('mobile', creme_fields.PhoneField(max_length=100, verbose_name='Mobile', blank=True)),
                ('skype', models.CharField(max_length=100, verbose_name=b'Skype', blank=True)),
                ('fax', models.CharField(max_length=100, verbose_name='Fax', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                ('url_site', models.URLField(max_length=500, verbose_name='Web Site', blank=True)),
                ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                ('billing_address',  models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),
                # ('image', models.ForeignKey(on_delete=SET_NULL, verbose_name='Photograph', blank=True, to='media_managers.Image', null=True)),
                ('image', ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Photograph', blank=True, null=True,
                                                to=settings.DOCUMENTS_DOCUMENT_MODEL,  # TODO: remove in deconstruct ?
                                               ),
                ),
                ('is_user', models.ForeignKey(related_name='related_contact', on_delete=SET_NULL, blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Related user')),
                ('position', models.ForeignKey(on_delete=SET_NULL, verbose_name='Position', blank=True, to='persons.Position', null=True)),
                ('full_position', models.CharField(max_length=500, verbose_name='Detailed position', blank=True)),
                ('sector', models.ForeignKey(on_delete=SET_NULL, verbose_name='Line of business', blank=True, to='persons.Sector', null=True)),
                ('language', models.ManyToManyField(verbose_name='Spoken language(s)', editable=False, to='creme_core.Language', blank=True)),
            ],
            options={
                'swappable': 'PERSONS_CONTACT_MODEL',
                'ordering': ('last_name', 'first_name'),
                'verbose_name': 'Contact',
                'verbose_name_plural': 'Contacts',
                'index_together': {('last_name', 'first_name', 'cremeentity_ptr')},
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('is_managed', models.BooleanField(default=False, verbose_name='Managed by Creme', editable=False)),
                ('phone', creme_fields.PhoneField(max_length=100, verbose_name='Phone number', blank=True)),
                ('fax', models.CharField(max_length=100, verbose_name='Fax', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                ('url_site', models.URLField(max_length=500, verbose_name='Web Site', blank=True)),
                ('capital', models.PositiveIntegerField(null=True, verbose_name='Capital', blank=True)),
                ('siren', models.CharField(max_length=100, verbose_name='SIREN', blank=True)),
                ('naf', models.CharField(max_length=100, verbose_name='NAF code', blank=True)),
                ('siret', models.CharField(max_length=100, verbose_name='SIRET', blank=True)),
                ('rcs', models.CharField(max_length=100, verbose_name='RCS/RM', blank=True)),
                ('tvaintra', models.CharField(max_length=100, verbose_name='VAT number', blank=True)),
                ('subject_to_vat', models.BooleanField(default=True, verbose_name='Subject to VAT')),
                ('annual_revenue', models.CharField(max_length=100, verbose_name='Annual revenue', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('creation_date', models.DateField(null=True, verbose_name='Date of creation of the organisation', blank=True)),
                ('billing_address',  models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),
                # ('image', models.ForeignKey(on_delete=SET_NULL, verbose_name='Logo', blank=True, to='media_managers.Image', null=True)),
                ('image', ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Logo', blank=True, null=True,
                                                to=settings.DOCUMENTS_DOCUMENT_MODEL,
                                               )
                ),
                ('legal_form', models.ForeignKey(on_delete=SET_NULL, verbose_name='Legal form', blank=True, to='persons.LegalForm', null=True)),
                ('sector', models.ForeignKey(on_delete=SET_NULL, verbose_name='Sector', blank=True, to='persons.Sector', null=True)),
                ('staff_size', models.ForeignKey(on_delete=SET_NULL, verbose_name='Staff size', blank=True, to='persons.StaffSize', null=True)),
            ],
            options={
                'swappable': 'PERSONS_ORGANISATION_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Organisation',
                'verbose_name_plural': 'Organisations',
                'index_together': {('name', 'cremeentity_ptr')},
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
