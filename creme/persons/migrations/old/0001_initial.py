from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, SET_NULL

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CREME_REPLACE_NULL
from creme.documents.models.fields import ImageEntityForeignKey
from creme.persons.models import address


class Migration(migrations.Migration):
    # replaces = [
    #     ('persons', '0001_initial'),
    #     ('persons', '0033_v2_6__is_staff_contact'),
    #     ('persons', '0034_v2_6__fix_uuids'),
    #     ('persons', '0035_v2_6__address_extra_data'),
    # ]
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
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                # ('zipcode', models.CharField(max_length=100, verbose_name='Zip code', blank=True)),
                ('zipcode', address.ZipCodeField(blank=True, max_length=100, verbose_name='Zip code')),
                # ('city', models.CharField(max_length=100, verbose_name='City', blank=True)),
                ('city', address.CityField(blank=True, max_length=100, verbose_name='City')),
                # ('department', models.CharField(max_length=100, verbose_name='Department', blank=True)),
                ('department', address.DepartmentField(blank=True, max_length=100, verbose_name='Department')),
                ('state', models.CharField(max_length=100, verbose_name='State', blank=True)),
                # ('country', models.CharField(max_length=40, verbose_name='Country', blank=True)),
                ('country', address.CountryField(blank=True, max_length=40, verbose_name='Country')),
                (
                    'object',
                    models.ForeignKey(
                        to='creme_core.CremeEntity',
                        editable=False, on_delete=CASCADE, related_name='persons_addresses',
                    )
                ),
                (
                    'content_type',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.ContentType',
                        editable=False, on_delete=CASCADE, related_name='+',
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                (
                    'civility',
                    models.ForeignKey(
                        verbose_name='Civility', to='persons.Civility',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                ('last_name', models.CharField(max_length=100, verbose_name='Last name')),
                ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                ('phone', core_fields.PhoneField(max_length=100, verbose_name='Phone', blank=True)),
                ('mobile', core_fields.PhoneField(max_length=100, verbose_name='Mobile', blank=True)),
                # ('skype', models.CharField(max_length=100, verbose_name='Skype', blank=True)),
                ('skype', models.CharField(max_length=100, verbose_name='Videoconference', blank=True)),
                ('fax', models.CharField(max_length=100, verbose_name='Fax', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                ('url_site', core_fields.CremeURLField(max_length=500, verbose_name='Web Site', blank=True)),
                ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address', to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address', to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'image',
                    ImageEntityForeignKey(
                        on_delete=SET_NULL, verbose_name='Photograph', blank=True, null=True,
                        to=settings.DOCUMENTS_DOCUMENT_MODEL,  # TODO: remove in deconstruct ?
                    ),
                ),
                (
                    'is_user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL, verbose_name='Related user',
                        related_name='related_contact', on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'position',
                    models.ForeignKey(
                        verbose_name='Position', to='persons.Position',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True
                    )
                ),
                ('full_position', models.CharField(max_length=500, verbose_name='Detailed position', blank=True)),
                (
                    'sector',
                    models.ForeignKey(
                        verbose_name='Line of business', to='persons.Sector',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'languages',
                    models.ManyToManyField(verbose_name='Spoken language(s)', to='creme_core.Language', blank=True)
                ),
            ],
            options={
                'swappable': 'PERSONS_CONTACT_MODEL',
                'ordering': ('last_name', 'first_name'),
                'verbose_name': 'Contact',
                'verbose_name_plural': 'Contacts',
                'indexes': [
                    models.Index(
                        fields=['last_name', 'first_name', 'cremeentity_ptr'],
                        name='persons__contact__default_lv',
                    ),
                ],
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                (
                    'is_managed',
                    models.BooleanField(
                        verbose_name=f'Managed by {settings.SOFTWARE_LABEL}',
                        default=False, editable=False,
                    )
                ),
                ('phone', core_fields.PhoneField(max_length=100, verbose_name='Phone', blank=True)),
                ('fax', models.CharField(max_length=100, verbose_name='Fax', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                ('url_site', core_fields.CremeURLField(max_length=500, verbose_name='Web Site', blank=True)),
                ('capital', models.PositiveIntegerField(null=True, verbose_name='Capital', blank=True)),
                ('siren', models.CharField(max_length=100, verbose_name='SIREN', blank=True)),
                ('naf', models.CharField(max_length=100, verbose_name='NAF code', blank=True)),
                ('siret', models.CharField(max_length=100, verbose_name='SIRET', blank=True)),
                ('rcs', models.CharField(max_length=100, verbose_name='RCS/RM', blank=True)),
                ('tvaintra', models.CharField(max_length=100, verbose_name='VAT number', blank=True)),
                ('subject_to_vat', models.BooleanField(default=True, verbose_name='Subject to VAT')),
                ('annual_revenue', models.CharField(max_length=100, verbose_name='Annual revenue', blank=True)),
                ('creation_date', models.DateField(null=True, verbose_name='Date of creation of the organisation', blank=True)),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address', to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address', to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'image',
                    ImageEntityForeignKey(
                        verbose_name='Logo', to=settings.DOCUMENTS_DOCUMENT_MODEL,
                        on_delete=SET_NULL, blank=True, null=True,
                    )
                ),
                (
                    'legal_form',
                    models.ForeignKey(
                        verbose_name='Legal form', to='persons.LegalForm',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'sector',
                    models.ForeignKey(
                        verbose_name='Sector', to='persons.Sector',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'staff_size',
                    models.ForeignKey(
                        verbose_name='Staff size', to='persons.StaffSize',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
            ],
            options={
                'swappable': 'PERSONS_ORGANISATION_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Organisation',
                'verbose_name_plural': 'Organisations',
                'indexes': [
                    models.Index(
                        fields=['name', 'cremeentity_ptr'], name='persons__orga__default_lv',
                    ),
                ],
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
