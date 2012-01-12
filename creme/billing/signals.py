# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

#from logging import debug

#from django.dispatch import receiver #Django 1.3
from django.db.models.signals import post_save, post_delete

#@receiver(form_post_save) #Django 1.3
from creme_core.models import Relation

from billing.constants import REL_SUB_CREDIT_NOTE_APPLIED, REL_OBJ_HAS_LINE


#TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
def manage_line_deletion(sender, instance, **kwargs):
    """Invoice calculated totals have to be refreshed"""
    if instance.type_id == REL_OBJ_HAS_LINE:
        instance.object_entity.get_real_entity().save()

def manage_linked_credit_notes(sender, instance, **kwargs):
    """Invoice calculated totals have to be refreshed."""
    if instance.type_id == REL_SUB_CREDIT_NOTE_APPLIED:
        instance.object_entity.get_real_entity().save()

def connect_to_signals():
    post_delete.connect(manage_line_deletion, sender=Relation)

    post_save.connect(manage_linked_credit_notes,   sender=Relation)
    post_delete.connect(manage_linked_credit_notes, sender=Relation)
