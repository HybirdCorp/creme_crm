################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

# import warnings
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.creme_core.global_info import cached_per_request
from creme.creme_core.models import CREME_REPLACE_NULL, CremeEntity
from creme.creme_core.models import fields as core_fields
from creme.creme_core.models.manager import CremeEntityManager
from creme.documents.models.fields import ImageEntityForeignKey

from .. import constants, get_contact_model
from . import base, other_models


class OrganisationManager(CremeEntityManager):
    @cached_per_request('persons-organisation-all_managed')
    def filter_managed_by_creme(self):
        return self.filter(is_managed=True, is_deleted=False)


class AbstractOrganisation(CremeEntity, base.PersonWithAddressesMixin):
    name = models.CharField(_('Name'), max_length=200)

    is_managed = models.BooleanField(
        lazy(
            lambda: gettext('Managed by {software}').format(software=settings.SOFTWARE_LABEL),
            str
        )(),
        default=False, editable=False,
    ).set_tags(clonable=False)

    phone    = core_fields.PhoneField(
        _('Phone'), max_length=100, blank=True,
    ).set_tags(optional=True)
    fax      = models.CharField(_('Fax'), max_length=100, blank=True).set_tags(optional=True)
    email    = models.EmailField(_('Email address'), blank=True).set_tags(optional=True)
    url_site = core_fields.CremeURLField(
        _('Web Site'), max_length=500, blank=True,
    ).set_tags(optional=True)

    sector = models.ForeignKey(
        other_models.Sector,
        verbose_name=_('Sector'), blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)
    legal_form = models.ForeignKey(
        other_models.LegalForm,
        verbose_name=_('Legal form'), blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)
    staff_size = models.ForeignKey(
        other_models.StaffSize,
        verbose_name=_('Staff size'), blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)

    capital = models.PositiveIntegerField(
        _('Capital'), blank=True, null=True,
    ).set_tags(optional=True)
    annual_revenue = models.CharField(
        _('Annual revenue'), max_length=100, blank=True,
    ).set_tags(optional=True)

    code = models.CharField(
        pgettext_lazy('persons-organisation', 'Code'),
        max_length=30, blank=True,
        help_text=_('Useful to distinguish your managed organisations'),
    ).set_tags(optional=True)

    siren = models.CharField(_('SIREN'),    max_length=100, blank=True).set_tags(optional=True)
    naf   = models.CharField(_('NAF code'), max_length=100, blank=True).set_tags(optional=True)
    siret = models.CharField(_('SIRET'),    max_length=100, blank=True).set_tags(optional=True)
    rcs   = models.CharField(_('RCS/RM'),   max_length=100, blank=True).set_tags(optional=True)

    eori = models.CharField(
        _('EORI number'), max_length=17, blank=True,
        help_text=_(
            'Economic Operators Registration and Identification number. '
            'Required for customs clearance in the EU.'
        ),
    ).set_tags(optional=True)

    tvaintra = models.CharField(
        _('VAT number'), max_length=100, blank=True,
    ).set_tags(optional=True)
    subject_to_vat = models.BooleanField(
        _('Subject to VAT'), default=True,
    ).set_tags(optional=True)

    creation_date = models.DateField(
        _('Date of creation of the organisation'), blank=True, null=True,
    ).set_tags(optional=True)

    image = ImageEntityForeignKey(
        verbose_name=_('Logo'), blank=True, null=True, on_delete=models.SET_NULL,
    ).set_tags(optional=True)

    objects = OrganisationManager()

    search_score = 102

    creation_label = _('Create an organisation')
    save_label = _('Save the organisation')

    class Meta:
        abstract = True
        app_label = 'persons'
        ordering = ('name',)
        verbose_name = _('Organisation')
        verbose_name_plural = _('Organisations')
        indexes = [
            models.Index(
                fields=['name', 'cremeentity_ptr'],
                name='persons__orga__default_lv',
            ),
        ]

    def __str__(self):
        return self.name

    def _check_deletion(self):
        # NB: it's important to NOT use a cached query, because the user could
        #     try to delete several managed Organisations at once, so the
        #     condition must be evaluated correctly before each deletion.
        if self.is_managed and self.__class__.objects.filter(is_managed=True).count() == 1:
            raise SpecificProtectedError(
                gettext('The last managed organisation cannot be deleted.'),
                [self]
            )

    def delete(self, *args, **kwargs):
        self._check_deletion()  # Should not be useful (trashing should be blocked too)
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('persons__view_organisation', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('persons__create_organisation')

    def get_edit_absolute_url(self):
        return reverse('persons__edit_organisation', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('persons__list_organisations')

    # TODO: use FilteredRelation ?
    def get_managers(self):
        return get_contact_model().objects.filter(
            is_deleted=False,
            relations__type=constants.REL_SUB_MANAGES,
            relations__object_entity=self.id,
        )

    # TODO: use FilteredRelation ?
    def get_employees(self):
        return get_contact_model().objects.filter(
            is_deleted=False,
            relations__type=constants.REL_SUB_EMPLOYED_BY,
            relations__object_entity=self.id,
        )

    # def _post_save_clone(self, source):
    #     warnings.warn(
    #         'The method Organisation._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     self._aux_post_save_clone(source)

    def trash(self):
        self._check_deletion()
        super().trash()


class Organisation(AbstractOrganisation):
    class Meta(AbstractOrganisation.Meta):
        swappable = 'PERSONS_ORGANISATION_MODEL'
