# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, SET_NULL

from creme.creme_core.models import CREME_REPLACE_NULL
from creme.creme_core.models import fields as creme_fields
from creme.documents.models.fields import ImageEntityForeignKey


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('contenttypes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('creme_core', '0001_initial'),
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
                ('object', models.ForeignKey(editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='persons_addresses')),
                ('content_type', creme_fields.EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType')),
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
                ('civility', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Civility', blank=True, to='persons.Civility', null=True)),
                ('last_name', models.CharField(max_length=100, verbose_name='Last name')),
                ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                ('phone', creme_fields.PhoneField(max_length=100, verbose_name='Phone number', blank=True)),
                ('mobile', creme_fields.PhoneField(max_length=100, verbose_name='Mobile', blank=True)),
                ('skype', models.CharField(max_length=100, verbose_name='Skype', blank=True)),
                ('fax', models.CharField(max_length=100, verbose_name='Fax', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                ('url_site', models.URLField(max_length=500, verbose_name='Web Site', blank=True)),
                ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                ('billing_address',  models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),
                ('image', ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Photograph', blank=True, null=True,
                                                to=settings.DOCUMENTS_DOCUMENT_MODEL,  # TODO: remove in deconstruct ?
                                                # limit_choices_to=models.Q(mime_type__name__startswith='image/'),
                                               ),
                ),
                ('is_user', models.ForeignKey(related_name='related_contact', on_delete=SET_NULL, blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Related user')),
                ('position', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Position', blank=True, to='persons.Position', null=True)),
                ('full_position', models.CharField(max_length=500, verbose_name='Detailed position', blank=True)),
                ('sector', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Line of business', blank=True, to='persons.Sector', null=True)),
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
                ('creation_date', models.DateField(null=True, verbose_name='Date of creation of the organisation', blank=True)),
                ('billing_address',  models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),
                ('image', ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Logo', blank=True, null=True,
                                                to=settings.DOCUMENTS_DOCUMENT_MODEL,
                                                # limit_choices_to=models.Q(mime_type__name__startswith='image/'),
                                               )
                ),
                ('legal_form', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Legal form', blank=True, to='persons.LegalForm', null=True)),
                ('sector', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Sector', blank=True, to='persons.Sector', null=True)),
                ('staff_size', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Staff size', blank=True, to='persons.StaffSize', null=True)),
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
