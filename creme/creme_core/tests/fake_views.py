# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from ..tests import fake_models, fake_forms


@login_required
@permission_required('creme_core')
def document_listview(request):
    return generic.list_view(request, fake_models.FakeDocument)


@login_required
@permission_required('creme_core')
def image_detailview(request, image_id):
    return generic.view_entity(request, image_id, fake_models.FakeImage)


@login_required
@permission_required('creme_core')
def image_listview(request):
    return generic.list_view(request, fake_models.FakeImage)


@login_required
@permission_required('creme_core')
@permission_required('creme_core.add_fakecontact')
def contact_add(request):
    return generic.add_entity(request, fake_forms.FakeContactForm)


@login_required
@permission_required('creme_core')
def contact_edit(request, contact_id):
    return generic.edit_entity(request, contact_id, fake_models.FakeContact,
                               fake_forms.FakeContactForm,
                              )


@login_required
@permission_required('creme_core')
def contact_detailview(request, contact_id):
    return generic.view_entity(request, contact_id, fake_models.FakeContact,
                               # '/tests/contact',
                              )


@login_required
@permission_required('creme_core')
def contact_listview(request):
    return generic.list_view(request, fake_models.FakeContact)


@login_required
#@permission_required('creme_core')
#@permission_required('creme_core.add_fakeorganisation')
@permission_required(('creme_core', 'creme_core.add_fakeorganisation'))
def organisation_add(request):
    return generic.add_entity(request, fake_forms.FakeOrganisationForm)


@login_required
@permission_required('creme_core')
def organisation_edit(request, orga_id):
    return generic.edit_entity(request, orga_id, fake_models.FakeOrganisation,
                               fake_forms.FakeOrganisationForm,
                              )


@login_required
@permission_required('creme_core')
def organisation_detailview(request, orga_id):
    return generic.view_entity(request, orga_id, fake_models.FakeOrganisation,
                               # '/tests/organisation',
                              )


@login_required
@permission_required('creme_core')
def organisation_listview(request):
    return generic.list_view(request, fake_models.FakeOrganisation)


@login_required
@permission_required('creme_core')
def address_add(request, entity_id):
    return generic.add_to_entity(request, entity_id, fake_forms.FakeAddressForm,
                                 _(u'Adding address to <%s>'),
                                 submit_label=_('Save the address'),
                                )


@login_required
@permission_required('creme_core')
def address_edit(request, address_id):
    return generic.edit_related_to_entity(request, address_id,
                                          fake_models.FakeAddress,
                                          fake_forms.FakeAddressForm,
                                          _(u"Address for <%s>"),
                                         )


@login_required
@permission_required('creme_core')
def activity_listview(request):
    return generic.list_view(request, fake_models.FakeActivity)


@login_required
@permission_required('creme_core')
def campaign_listview(request):
    return generic.list_view(request, fake_models.FakeEmailCampaign)


@login_required
@permission_required('creme_core')
def invoice_detailview(request, invoice_id):
    return generic.view_entity(request, invoice_id, fake_models.FakeInvoice,
                               # '/tests/invoice',
                              )


@login_required
@permission_required('creme_core')
def invoice_listview(request):
    return generic.list_view(request, fake_models.FakeInvoice)


@login_required
@permission_required('creme_core')
def invoice_lines_listview(request):
    return generic.list_view(request, fake_models.FakeInvoiceLine, show_actions=False)
