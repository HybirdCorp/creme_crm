# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core import models as creme_models
from creme.creme_core.models import fields as creme_fields
from creme.creme_core.utils import ellipsis


class MemoManager(models.Manager):
    def filter_by_user(self, user):
        return self.filter(user__in=[user, *user.teams])


class Memo(creme_models.CremeModel):
    user = creme_fields.CremeUserForeignKey(verbose_name=_('Owner user'))
    content = models.TextField(_('Content'))
    on_homepage = models.BooleanField(_('Displayed on homepage'), default=False)
    creation_date = creme_fields.CreationDateTimeField(_('Creation date'), editable=False)

    entity_content_type = creme_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        creme_models.CremeEntity,  related_name='assistants_memos',
        editable=False, on_delete=models.CASCADE,
    ).set_tags(viewable=False)
    creme_entity = creme_fields.RealEntityForeignKey(
        ct_field='entity_content_type', fk_field='entity',
    )

    objects = MemoManager()

    creation_label = _('Create a memo')
    save_label     = _('Save the memo')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Memo')
        verbose_name_plural = _('Memos')

    def __str__(self):
        # NB: translate for unicode can not take 2 arguments...
        return ellipsis(self.content.strip().replace('\n', ''), 25)

    def get_edit_absolute_url(self):
        return reverse('assistants__edit_memo', args=(self.id,))

    def get_related_entity(self):  # For generic views
        return self.creme_entity
