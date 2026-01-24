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

from django.conf import Settings

from creme.creme_core.apps import CremeAppConfig


class EditorConfig(CremeAppConfig):
    default = True
    name = "creme.editor"
    verbose_name = "Editor"
    credentials = CremeAppConfig.CRED_NONE
    dependencies = ["creme.creme_core"]

    def setup_media_bundles(self, settings: Settings):
        settings.CREME_OPT_MEDIA_BUNDLES.append([
            'editor-tinymce.js',
            # 'editor/js/lib/tinymce.min.8.3.2.js',
            # 'editor/js/lib/plugins/accordion/plugin.min.js',
            # 'editor/js/lib/plugins/advlist/plugin.min.js',
            # 'editor/js/lib/plugins/anchor/plugin.min.js',
            # 'editor/js/lib/plugins/autolink/plugin.min.js',
            # 'editor/js/lib/plugins/autoresize/plugin.min.js',
            # 'editor/js/lib/plugins/autosave/plugin.min.js',
            # 'editor/js/lib/plugins/charmap/plugin.min.js',
            # 'editor/js/lib/plugins/code/plugin.min.js',
            # 'editor/js/lib/plugins/codesample/plugin.min.js',
            # 'editor/js/lib/plugins/directionality/plugin.min.js',
            # 'editor/js/lib/plugins/emoticons/plugin.min.js',
            # 'editor/js/lib/plugins/fullscreen/plugin.min.js',
            # 'editor/js/lib/plugins/help/plugin.min.js',
            # 'editor/js/lib/plugins/image/plugin.min.js',
            # 'editor/js/lib/plugins/importcss/plugin.min.js',
            # 'editor/js/lib/plugins/insertdatetime/plugin.min.js',
            # 'editor/js/lib/plugins/link/plugin.min.js',
            # 'editor/js/lib/plugins/lists/plugin.min.js',
            # 'editor/js/lib/plugins/media/plugin.min.js',
            # 'editor/js/lib/plugins/nonbreaking/plugin.min.js',
            # 'editor/js/lib/plugins/pagebreak/plugin.min.js',
            # 'editor/js/lib/plugins/preview/plugin.min.js',
            # 'editor/js/lib/plugins/quickbars/plugin.min.js',
            # 'editor/js/lib/plugins/save/plugin.min.js',
            # 'editor/js/lib/plugins/searchreplace/plugin.min.js',
            # 'editor/js/lib/plugins/table/plugin.min.js',
            # 'editor/js/lib/plugins/visualblocks/plugin.min.js',
            # 'editor/js/lib/plugins/visualchars/plugin.min.js',
            # 'editor/js/lib/plugins/wordcount/plugin.min.js',
            'editor/js/lib/tinymce-bundle-8.3.2.js',
            'editor/js/form/tinymceditor.js',
            'editor/js/editor.js',
        ])

        for theme, _, in settings.THEMES:
            settings.CREME_OPT_MEDIA_BUNDLES.append([
                f'{theme}editor-tinymce.css',
                f'{theme}/editor/css/tinymce-oxide.css',
                f'{theme}/editor/css/tinymce-creme.css',
            ])
