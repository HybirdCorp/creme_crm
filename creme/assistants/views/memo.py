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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.views import generic

from ..forms.memo import MemoForm
from ..models import Memo


class MemoCreation(generic.AddingInstanceToEntityPopup):
    model = Memo
    form_class = MemoForm
    title = _('New memo for «{entity}»')


class MemoEdition(generic.RelatedToEntityEditionPopup):
    model = Memo
    form_class = MemoForm
    pk_url_kwarg = 'memo_id'
    title = _('Memo for «{entity}»')
