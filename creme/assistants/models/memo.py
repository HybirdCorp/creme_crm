# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db.models import TextField, BooleanField, DateTimeField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User

from creme_core.models import CremeModel, CremeEntity


class Memo(CremeModel):
    content       = TextField(_(u'Content'), blank=True, null=True)
    on_homepage   = BooleanField(_(u"Displayed on homepage"), blank=True, default=False)
    creation_date = DateTimeField(_(u'Creation date'), blank=True, null=True)
    user          = ForeignKey(User, verbose_name=_(u'Assigned to'), blank=True, null=True, related_name='user_memo_assigned_set')

    entity_content_type = ForeignKey(ContentType, related_name="memo_entity_set")
    entity_id           = PositiveIntegerField()
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    @staticmethod
    def get_memos(entity_pk):
        return Memo.objects.filter(entity_id=entity_pk)

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Memo')
        verbose_name_plural = _(u'Memos')


#TODO: can delete this with  a WeakForeignKey ??
def dispose_entity_memos(sender, instance, **kwargs):
    Memo.get_memos(instance.id).delete()

pre_delete.connect(dispose_entity_memos, sender=CremeEntity)
