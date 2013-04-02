# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.conf import settings
from django.forms.fields import ChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.base import CremeForm
from creme.creme_core.utils.media import get_current_theme

from ..constants import USER_THEME_NAME
from ..models import SettingValue, SettingKey


class UserThemeForm(CremeForm):
    themes = ChoiceField(label=_(u"Choose your theme"), choices=settings.THEMES,
                         widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form));'}),
                         help_text=_(u"Think to reload the page once you changed the theme.")
                        )

    def __init__(self, user, *args, **kwargs):
        super(UserThemeForm, self).__init__(user, *args, **kwargs)
        self.fields['themes'].initial = get_current_theme()

    def save(self, *args, **kwargs):
        try:
            sv = SettingValue.objects.get(user=self.user, key=USER_THEME_NAME)
        except SettingValue.DoesNotExist:
            sk = SettingKey.objects.get(pk=USER_THEME_NAME)
            sv = SettingValue.objects.create(user=self.user, key=sk)

        sv.value = self.cleaned_data['themes']
        sv.save()

    def as_span(self):#TODO: In CremeForm?
        """Returns this form rendered as HTML <span>s."""
        return self._html_output(normal_row=u'<span%(html_class_attr)s>%(label)s %(field)s%(help_text)s</span>',
                                 error_row=u'%s',
                                 row_ender='</span>',
                                 help_text_html=u' <span class="helptext">%s</span>',
                                 errors_on_separate_row=False,
                                )
