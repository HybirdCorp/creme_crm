################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from __future__ import annotations

from django.forms import widgets


class TinyMCEEditor(widgets.Textarea):
    template_name = 'editor/forms/tinymceditor.html'
    TOOLBARS = {'full', 'simple'}

    class Media:
        css = {
            "all": [
                "editor-tinymce.css",
            ]
        }
        js = [
            "editor-tinymce.js",
        ]

    def __init__(self, attrs=None, toolbar='full', upload_url=None):
        super().__init__(attrs=attrs)
        self.toolbar = toolbar
        self.upload_url = upload_url

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        is_auto = context['widget']['attrs'].pop('auto', True)

        context['creme_widget_auto'] = is_auto
        context['editor_toolbar'] = self.toolbar
        context['editor_upload_url'] = self.upload_url or ''
        context['editor_path'] = 'tiny_mce'

        return context
