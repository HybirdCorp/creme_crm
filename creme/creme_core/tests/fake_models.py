from typing import Tuple

from django.conf import settings

__all__: Tuple[str, ...]

if not settings.TESTS_ON:
    __all__ = ()
else:
    from decimal import Decimal

    from django.core.exceptions import ValidationError
    from django.db import models
    from django.db.models.query_utils import Q
    from django.urls import reverse
    from django.utils.translation import gettext
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import pgettext_lazy

    # from ..constants import DEFAULT_CURRENCY_PK
    from ..core.entity_filter import EF_REGULAR
    from ..models import (
        CremeEntity,
        CremeModel,
        Currency,
        EntityFilter,
        Language,
        MinionModel,
        Vat,
        deletion,
    )
    from ..models import fields as core_fields
    from ..models.currency import get_default_currency_pk

    __all__ = (
        'FakeFolderCategory', 'FakeFolder',
        'FakeDocumentCategory', 'FakeDocument',
        'FakeFileComponent', 'FakeFileBag',
        'FakeImageCategory', 'FakeImage',
        'FakeCivility', 'FakePosition', 'FakeSector', 'FakeAddress', 'FakeCountry',
        'FakeContact', 'FakeLegalForm', 'FakeOrganisation',
        'FakeActivityType', 'FakeActivity',
        'FakeMailingList', 'FakeEmailCampaign',
        'FakeInvoice', 'FakeInvoiceLine',
        'FakeProductType', 'FakeProduct',
        'FakeReport',
        'FakeTicketStatus', 'FakeTicketPriority', 'FakeTicket',
        'FakeIngredient', 'FakeRecipe',
        'FakeTodoCategory', 'FakeTodo',
        'FakeSkill', 'FakeTraining',
    )

    # NB: not MinionModel to test future errors (maybe)
    class FakeFolderCategory(CremeModel):
        name = models.CharField(_('Category name'), max_length=100, unique=True)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Folder category'
            verbose_name_plural = 'Test Folder categories'
            ordering = ('name',)

    class FakeFolder(CremeEntity):
        title = models.CharField(_('Title'), max_length=100)
        parent = models.ForeignKey(
            'self', verbose_name=_('Parent folder'),
            blank=True, null=True, related_name='children',
            on_delete=models.CASCADE,  # TODO: PROTECT
        )
        category = models.ForeignKey(
            FakeFolderCategory, verbose_name=_('Category'),
            blank=True, null=True, on_delete=models.SET_NULL,
            # related_name='folder_category_set',
        )

        # allowed_related = CremeEntity.allowed_related | {'document'}
        # creation_label = _('Create a folder')

        class Meta:
            app_label = 'creme_core'
            # unique_together = ('title', 'parent', 'category')
            verbose_name = 'Test Folder'
            verbose_name_plural = 'Test Folders'
            ordering = ('title',)

        def __str__(self):
            return self.title

    # NB: not MinionModel to test future errors (maybe)
    class FakeDocumentCategory(CremeModel):
        name = models.CharField(_('Category name'), max_length=100, unique=True)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Document category'
            verbose_name_plural = 'Test Document categories'
            ordering = ('name',)

    class FakeDocument(CremeEntity):
        title = models.CharField(_('Title'), max_length=100)
        filedata = models.FileField(
            _('File'), max_length=100, upload_to='creme_core-tests',
        ).set_tags(optional=True)
        linked_folder = models.ForeignKey(
            FakeFolder, verbose_name=_('Folder'), on_delete=models.PROTECT,
        )
        categories = models.ManyToManyField(
            FakeDocumentCategory,
            verbose_name=_('Categories'), related_name='+', blank=True,
        ).set_tags(optional=True)

        # creation_label = _('Create a document')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Document'
            verbose_name_plural = 'Test Documents'
            ordering = ('title',)

        def __str__(self):
            return f'{self.linked_folder} - {self.title}'

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_document', args=(self.id,))

        # def get_edit_absolute_url(self):
        # def get_download_absolute_url(self):  TODO ??

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_documents')

    class FakeFileComponent(CremeModel):
        filedata = models.FileField(
            _('File'), max_length=100, upload_to='creme_core-tests',
            null=True, blank=True,
        )

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test File component'
            verbose_name_plural = 'Test File components'

    class FakeFileBag(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        # NB: it's not really useful to use FakeFileComponent instead of FileField
        #     directly of course, but we need to test sub-FileField
        file1 = models.ForeignKey(
            FakeFileComponent, verbose_name='First file',
            null=True, blank=True, on_delete=models.PROTECT,
        ).set_tags(enumerable=False)

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test File bag'
            verbose_name_plural = 'Test File bags'
            ordering = ('name',)

    class FakeImageCategory(MinionModel):
        name = models.CharField(_('Name'), max_length=100)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Image category'
            verbose_name_plural = 'Test Image categories'
            ordering = ('name',)

    class FakeImage(CremeEntity):
        name = models.CharField(_('Name'), max_length=100, blank=True)  # null=True
        # image = models.ImageField(
        #     _('Image'), height_field='height', width_field='width',
        #     upload_to='upload/images', max_length=500,
        # )
        filedata = models.FileField(
            _('File'), max_length=100, editable=False, upload_to='creme_core-tests',
        )
        categories = models.ManyToManyField(
            FakeImageCategory, verbose_name=_('Categories'), related_name='+', blank=True,
        )
        exif_date = models.DateField(
            _('Exif date'), blank=True, null=True,
        ).set_tags(optional=True)

        # creation_label = _('Create an image')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Image'
            verbose_name_plural = 'Test Images'
            ordering = ('name',)

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_image', args=(self.id,))

        # @staticmethod
        # def get_clone_absolute_url():
        #     return ''

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_images')

        # def get_edit_absolute_url(self):

    class FakeCivility(MinionModel):
        title = models.CharField(_('Title'), max_length=100)
        shortcut = models.CharField(_('Shortcut'), max_length=100)

        # NB: do not define (see
        #     creme.creme_config.tests.test_generics_views.GenericModelConfigTestCase.test_add01()
        # )
        # creation_label = _('Create a civility')
        # save_label     = _('Save the civility')

        def __str__(self):
            return self.title

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test civility'
            verbose_name_plural = 'Test civilities'
            ordering = ('title',)

    class FakePosition(MinionModel):
        title = models.CharField(_('Title'), max_length=100)

        def __str__(self):
            return self.title

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test People position'
            verbose_name_plural = 'Test People positions'
            ordering = ('title',)

    class FakeSector(MinionModel):
        title = models.CharField(_('Title'), max_length=100)
        order = core_fields.BasicAutoField()  # Used by creme_config

        creation_label = _('Create a sector')
        save_label     = _('Save the sector')

        def __str__(self):
            return self.title

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test sector'
            verbose_name_plural = 'Test sectors'
            ordering = ('order',)

    class FakeAddress(CremeModel):
        value = models.TextField(_('Address'), blank=True)
        zipcode = models.CharField(
            _('Zip code'), max_length=100, blank=True,
        ).set_tags(optional=True)
        city = models.CharField(
            _('City'), max_length=100, blank=True,
        ).set_tags(optional=True)
        department = models.CharField(
            _('Department'), max_length=100, blank=True,
        ).set_tags(optional=True)
        country = models.CharField(
            _('Country'), max_length=40, blank=True,
        ).set_tags(optional=True)

        entity = models.ForeignKey(
            CremeEntity, related_name='+', editable=False, on_delete=models.CASCADE,
        ).set_tags(viewable=False)

        creation_label = _('Create an address')
        save_label     = _('Save the address')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test address'
            verbose_name_plural = 'Test addresses'
            # See test_listview.ListViewTestCase.test_ordering_related_column()
            # ordering = ('id',)

        def __str__(self):
            return ' '.join(filter(
                None, [self.value, self.zipcode, self.city, self.department, self.country],
            ))

        def get_edit_absolute_url(self):
            return reverse('creme_core__edit_fake_address', args=(self.id,))

        def get_related_entity(self):  # For generic views
            return self.entity

    class FakeCountry(MinionModel):
        name = models.CharField(_('Name'), max_length=100)

        # creation_label = 'Create a country'
        # save_label     = 'Save the country'

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test country'
            verbose_name_plural = 'Test countries'
            ordering = ('name',)

    class FakeContact(CremeEntity):
        civility = models.ForeignKey(
            FakeCivility, verbose_name=_('Civility'), blank=True, null=True,
            on_delete=deletion.CREME_REPLACE_NULL,
        ).set_tags(optional=True)
        last_name  = models.CharField(_('Last name'), max_length=100)
        first_name = models.CharField(
            _('First name'), max_length=100, blank=True,
        ).set_tags(optional=True)

        is_a_nerd = models.BooleanField(_('Is a Nerd'), default=False)
        loves_comics = models.BooleanField(_('Loves comics'), default=None, null=True, blank=True)

        # NB: keep nullable for some tests
        phone = core_fields.PhoneField(
            _('Phone'), max_length=100, blank=True, null=True,
        ).set_tags(optional=True)
        mobile = core_fields.PhoneField(
            _('Mobile'), max_length=100, blank=True,  # null=True,
        ).set_tags(optional=True)
        email = models.EmailField(_('Email address'), max_length=100, blank=True)
        # url_site = models.URLField(_('Web Site'), max_length=500, blank=True)
        url_site = core_fields.CremeURLField(_('Web Site'), max_length=500, blank=True)

        position = models.ForeignKey(
            FakePosition, verbose_name=_('Position'),
            blank=True, null=True, on_delete=models.SET_NULL,
        ).set_tags(optional=True)
        sector = models.ForeignKey(
            FakeSector, verbose_name=_('Line of business'), blank=True, null=True,
            # on_delete=models.SET_NULL,
            on_delete=deletion.CREME_REPLACE_NULL,
            limit_choices_to=lambda: ~Q(title='[INVALID]'),
        ).set_tags(optional=True)

        languages = models.ManyToManyField(
            Language, verbose_name=_('Spoken language(s)'), blank=True,
            limit_choices_to=~Q(name__contains='[deprecated]'),
        )
        preferred_countries = models.ManyToManyField(
            FakeCountry, verbose_name='Preferred countries', blank=True,
        ).set_tags(clonable=False)
        address = models.ForeignKey(
            FakeAddress, verbose_name=_('Billing address'),
            blank=True, null=True, editable=False,
            related_name='+', on_delete=models.SET_NULL,
        ).set_tags(enumerable=False)  # clonable=False useless

        is_user = models.ForeignKey(
            settings.AUTH_USER_MODEL, verbose_name=_('Related user'),
            blank=True, null=True, editable=False,
            related_name='+',
            on_delete=models.SET_NULL,
        ).set_tags(
            clonable=False, enumerable=False,
        ).set_null_label(pgettext_lazy('persons-is_user', 'None'))

        birthday = models.DateField(_('Birthday'), blank=True, null=True).set_tags(optional=True)

        image = models.ForeignKey(
            FakeImage, verbose_name=_('Photograph'),
            blank=True, null=True, on_delete=models.SET_NULL,
        ).set_tags(optional=True)

        search_score = 101
        creation_label = _('Create a contact')
        save_label     = _('Save the contact')

        class Meta:
            app_label = 'creme_core'
            ordering = ('last_name', 'first_name')
            verbose_name = 'Test Contact'
            verbose_name_plural = 'Test Contacts'
            indexes = [
                models.Index(
                    fields=['last_name', 'first_name', 'cremeentity_ptr'],
                    name='core__fakecontact__default_lv',
                ),
            ]

        def __str__(self):
            return '{} {} {}'.format(self.civility or '', self.first_name, self.last_name).strip()

        def clean(self):
            if self.is_user_id and not self.first_name:
                raise ValidationError(
                    gettext('This Contact is related to a user and must have a first name.')
                )

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_contact', args=(self.id,))

        @staticmethod
        def get_create_absolute_url():
            return reverse('creme_core__create_fake_contact')

        def get_edit_absolute_url(self):
            return reverse('creme_core__edit_fake_contact', args=(self.id,))

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_contacts')

    class FakeLegalForm(MinionModel):
        title = models.CharField(_('Title'), max_length=100)

        def __str__(self):
            return self.title

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Legal form'
            verbose_name_plural = 'Test Legal forms'
            ordering = ('title',)

    class FakeOrganisation(CremeEntity):
        name = models.CharField(_('Name'), max_length=200)
        phone = core_fields.PhoneField(_('Phone'), max_length=100, blank=True)
        email = models.EmailField(_('Email address'), max_length=100, blank=True)

        # NB: keep nullable for some tests
        url_site = models.URLField(
            _('Web Site'), max_length=500, blank=True, null=True,
        ).set_tags(optional=True)
        sector = models.ForeignKey(
            FakeSector, verbose_name=_('Sector'), blank=True, null=True,
            on_delete=deletion.CREME_REPLACE,
        ).set_tags(optional=True)
        capital = models.PositiveIntegerField(
            _('Capital'), blank=True, null=True,
        ).set_tags(optional=True)
        subject_to_vat = models.BooleanField(_('Subject to VAT'), default=True)

        legal_form = models.ForeignKey(
            FakeLegalForm, verbose_name=_('Legal form'),
            blank=True, null=True,
            on_delete=deletion.CREME_REPLACE_NULL,
            # NB: see creme_config.tests
            #                     .test_generics_views
            #                     .GenericModelConfigTestCase
            #                     .test_delete_hidden_related()
            related_name='+',
            limit_choices_to={'title__endswith': '[OK]'},
        )
        address = models.ForeignKey(
            FakeAddress, verbose_name=_('Billing address'),
            blank=True, null=True, editable=False,
            related_name='+', on_delete=models.SET_NULL,
        ).set_tags(enumerable=False)
        creation_date = models.DateField(_('Date of creation'), blank=True, null=True)
        image = models.ForeignKey(
            FakeImage, verbose_name=_('Logo'),
            blank=True, null=True, on_delete=models.SET_NULL,
            limit_choices_to=lambda: {'user__is_staff': False},
        )

        search_score = 102
        creation_label = _('Create an organisation')
        save_label = _('Save the organisation')

        class Meta:
            app_label = 'creme_core'
            ordering = ('name',)
            verbose_name = 'Test Organisation'
            verbose_name_plural = 'Test Organisations'
            indexes = [
                models.Index(
                    fields=['name', 'cremeentity_ptr'],
                    name='core__fakeorga__default_lv',
                ),
            ]

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_organisation', args=(self.id,))

        @staticmethod
        def get_create_absolute_url():
            return reverse('creme_core__create_fake_organisation')

        def get_edit_absolute_url(self):
            return reverse('creme_core__edit_fake_organisation', args=(self.id,))

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_organisations')

    class FakeActivityType(MinionModel):
        name = models.CharField(_('Name'), max_length=100, unique=True)
        order = core_fields.BasicAutoField()  # Used by creme_config

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Type of activity'
            verbose_name_plural = 'Test Types of activity'
            ordering = ('name',)

    class FakeActivity(CremeEntity):
        title = models.CharField(_('Title'), max_length=100, unique=True)
        place = models.CharField(_('Place'), max_length=100, blank=True)
        minutes = models.TextField(_('Minutes'), blank=True)

        start = models.DateTimeField(_('Start'), blank=True, null=True)
        end = models.DateTimeField(_('End'), blank=True, null=True)

        type = models.ForeignKey(
            FakeActivityType, verbose_name=_('Activity type'), on_delete=models.PROTECT,
            # editable=False,
        ).set_tags(optional=True)

        # creation_label = _('Create an activity')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Activity'
            verbose_name_plural = 'Test Activities'
            ordering = ('-start',)

        def __str__(self):
            return self.title

        # def get_absolute_url(self):
        # def get_edit_absolute_url(self):

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_activities')

    class FakeMailingList(CremeEntity):
        name = models.CharField(_('Name of the mailing list'), max_length=80)

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Mailing list'
            verbose_name_plural = 'Test Mailing lists'
            ordering = ('name',)

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_mlist', args=(self.id,))

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_mlists')

    class FakeEmailCampaign(CremeEntity):
        class Type(models.IntegerChoices):
            INTERNAL    = 1, 'Internal',
            EXTERNAL    = 2, 'External',

        class Status(models.IntegerChoices):
            WAITING    = 1, 'Waiting',
            SENT_OK    = 2, 'Sent',
            SENT_ERROR = 3, 'Sent (errors)',

        name = models.CharField(_('Name of the campaign'), max_length=100)
        type = models.PositiveIntegerField(
            # 'Type', choices=Type.choices, null=True, default=None,
            'Type', choices=Type, null=True, default=None,
        )
        status = models.PositiveIntegerField(
            # 'Status', choices=Status.choices, default=Status.WAITING,
            'Status', choices=Status, default=Status.WAITING,
        )
        mailing_lists = models.ManyToManyField(
            FakeMailingList, verbose_name=_('Related mailing lists'), blank=True,
        )

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test campaign'
            verbose_name_plural = 'Test campaigns'
            ordering = ('name',)

        def __str__(self):
            return self.name

        # def get_absolute_url(self):
        # def get_edit_absolute_url(self):

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_ecampaigns')

    class FakeInvoice(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        number = models.CharField(_('Number'), max_length=100, blank=True)
        issuing_date = models.DateField(_('Issuing date'), blank=True, null=True)
        expiration_date = models.DateField(
            _('Expiration date'), blank=True, null=True,
        ).set_tags(optional=True)
        currency = models.ForeignKey(
            Currency, verbose_name=_('Currency'), related_name='+',
            # default=DEFAULT_CURRENCY_PK,
            default=get_default_currency_pk,
            on_delete=models.PROTECT,
        )

        periodicity = core_fields.DatePeriodField(
            _('Periodicity of the generation'), blank=True, null=True,
            # See .models.test_fields.DatePeriodFieldTestCase.test_ok()
            # default={'type': 'months', 'value': 1},
        )

        total_vat = core_fields.MoneyField(
            _('Total with VAT'), max_digits=14, decimal_places=2,
            null=True, editable=False, default=0,
        )
        total_no_vat = core_fields.MoneyField(
            _('Total without VAT'), max_digits=14, decimal_places=2,
            null=True, editable=False, default=0,
        ).set_tags(optional=True)

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Invoice'
            verbose_name_plural = 'Test Invoices'
            # ordering = ('name',)
            ordering = ('name', '-expiration_date')

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_invoice', args=(self.id,))

        # def get_edit_absolute_url(self):

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_invoices')

    class FakeInvoiceLine(CremeEntity):
        class Discount(models.IntegerChoices):
            PERCENT = 1, _('Percent'),
            AMOUNT  = 2, _('Amount'),

        linked_invoice = models.ForeignKey(FakeInvoice, on_delete=models.CASCADE)
        item = models.CharField('Item', max_length=100, blank=True, null=True)
        quantity = models.DecimalField(
            _('Quantity'), max_digits=10, decimal_places=2, default=Decimal('1.00'),
        )
        unit_price = models.DecimalField(
            _('Unit price'), default=Decimal(), max_digits=10, decimal_places=2,
        )
        discount = models.DecimalField(
            _('Discount'), default=Decimal(), max_digits=10, decimal_places=2,
        )
        discount_unit = models.PositiveIntegerField(
            _('Discount Unit'), blank=True, null=True,
            # choices=Discount.choices, default=Discount.PERCENT,
            choices=Discount, default=Discount.PERCENT,
        )
        vat_value = models.ForeignKey(
            Vat, verbose_name=_('VAT'), blank=True, null=True,
            on_delete=models.PROTECT,
        )

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Invoice Line'
            verbose_name_plural = 'Test Invoice Lines'
            ordering = ('created',)

        @staticmethod
        def get_lv_absolute_url():
            return reverse('creme_core__list_fake_invoicelines')

        def get_related_entity(self):  # For generic views & delete
            return self.linked_invoice

    class FakeProductType(MinionModel):
        name = models.CharField(_('Name'), max_length=100)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Product type'
            verbose_name_plural = 'Test Product types'
            ordering = ('name',)

    class FakeProduct(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        type = models.ForeignKey(
            FakeProductType, verbose_name=_('Type'),
            on_delete=models.CASCADE, null=True, blank=True,
        ).set_tags(optional=True)
        images = models.ManyToManyField(
            FakeImage, blank=True, verbose_name=_('Images'),
            limit_choices_to={'user__is_active': True},
            # related_name='products',
        )
        creation_year = core_fields.YearField('Creation year', null=True, blank=True)

        # creation_label = _('Create a product')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Product'
            verbose_name_plural = 'Test Products'
            ordering = ('name',)

        def __str__(self):
            return self.name

        # def get_absolute_url(self):

        # NB: no get_lv_absolute_url(()  (see views.test_header_filter)

    class FakeReport(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        ctype = core_fields.EntityCTypeForeignKey(verbose_name=_('Entity type'))
        efilter = models.ForeignKey(
            EntityFilter, verbose_name=_('Filter'),
            blank=True, null=True, on_delete=models.PROTECT,
            limit_choices_to={'filter_type': EF_REGULAR},
        ).set_null_label(_('No filter'))

        # creation_label = _('Create a report')
        # save_label     = _('Save the report')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Report'
            verbose_name_plural = 'Test Reports'
            ordering = ('name',)

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('creme_core__view_fake_report', args=(self.id,))

    class FakeTicketStatus(MinionModel):
        name = models.CharField(_('Name'), max_length=100)
        color = core_fields.ColorField(verbose_name=_('Color'), default='ff0000')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Ticket status'
            verbose_name_plural = 'Test Ticket status'
            ordering = ('name',)

        def __str__(self):
            return self.name

    class FakeTicketPriority(MinionModel):
        name = models.CharField(_('Name'), max_length=100)

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Ticket priority'
            verbose_name_plural = 'Test Ticket priorities'
            ordering = ('name',)

        def __str__(self):
            return self.name

    def get_sentinel_priority():
        return FakeTicketPriority.objects.get_or_create(name='Deleted')[0]

    # No list-view; see test_fk_printer_html__content_type02
    class FakeTicket(CremeEntity):
        title = models.CharField(_('Title'), max_length=100)
        status = models.ForeignKey(
            FakeTicketStatus,
            verbose_name=_('Status'), on_delete=models.SET_DEFAULT, default=1,
        ).set_tags(optional=True)
        priority = models.ForeignKey(
            FakeTicketPriority, verbose_name=_('Priority'),
            on_delete=models.SET(get_sentinel_priority), default=3,
        ).set_tags(optional=True)

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Ticket'
            verbose_name_plural = 'Test Tickets'
            ordering = ('title',)

        def __str__(self):
            return self.title

        # def get_delete_absolute_url(self):
        #     return ''

    # TODO: MinionModel?
    class FakeIngredientGroup(CremeModel):
        name = models.CharField(_('Name'), max_length=100)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Ingredient Group'
            verbose_name_plural = 'Test Ingredient Groups'
            ordering = ('name',)

    class FakeIngredient(MinionModel):
        name = models.CharField(_('Name'), max_length=100)
        group = models.ForeignKey(
            FakeIngredientGroup,  related_name='ingredients',
            null=True, blank=True,
            on_delete=models.SET_DEFAULT, default=None
        )

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Ingredient'
            verbose_name_plural = 'Test Ingredients'
            ordering = ('name',)

    class FakeRecipe(CremeEntity):
        name = models.CharField(_('Name'), max_length=100)
        ingredients = models.ManyToManyField(
            FakeIngredient, verbose_name=_('Ingredients'), related_name='+',
            # NB: see creme_config.tests
            #                     .test_generics_views
            #                     .GenericModelConfigTestCase
            #                     .test_delete_m2m_03
            blank=False,
        )

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Recipe'
            verbose_name_plural = 'Test Recipes'
            ordering = ('name',)

        def __str__(self):
            return self.name

    # TODO: MinionModel
    class FakeTodoCategory(CremeModel):
        name = models.CharField(_('Name'), max_length=100, unique=True)

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test ToDo category'
            verbose_name_plural = 'Test ToDo categories'
            ordering = ('name',)

    class FakeTodo(CremeModel):
        title = models.CharField(_('Title'), max_length=200)
        # is_ok = models.BooleanField(_('Done?'), editable=False, default=False)
        # reminded = models.BooleanField(_('Notification sent'), editable=False, default=False)
        description = models.TextField(_('Description'), blank=True)
        categories = models.ManyToManyField(
            FakeTodoCategory,
            verbose_name=_('Categories'), related_name='+', blank=True,
        )

        entity_content_type = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
        entity = models.ForeignKey(
            CremeEntity,  related_name='fake_todos',
            editable=False, on_delete=models.CASCADE,
        ).set_tags(viewable=False)
        creme_entity = core_fields.RealEntityForeignKey(
            ct_field='entity_content_type', fk_field='entity',
        )

        # creation_label = _('Create a todo')
        # save_label     = _('Save the todo')

        class Meta:
            app_label = 'creme_core'
            verbose_name = 'Test Todo'
            verbose_name_plural = 'Test Todos'

        def __str__(self):
            return self.title

        def get_related_entity(self):  # To be recognised as an auxiliary
            return self.creme_entity

    # TODO: MinionModel?
    class FakeSkill(CremeModel):
        name = models.CharField(_('Name'), max_length=100)

        class Meta:
            app_label = 'creme_core'
            ordering = ('name',)
            verbose_name = 'Test Skill'
            verbose_name_plural = 'Test Skills'

    # TODO: MinionModel?
    class FakeTraining(CremeModel):
        name = models.CharField(_('Name'), max_length=100)
        skills = models.ManyToManyField(
            FakeSkill, verbose_name='Skills', blank=True, related_name='training',
        )

        class Meta:
            app_label = 'creme_core'
            ordering = ('name',)
            verbose_name = 'Test Training'
            verbose_name_plural = 'Test Training'
