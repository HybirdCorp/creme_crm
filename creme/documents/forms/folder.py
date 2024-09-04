################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from django.db.models.query_utils import Q
from django.utils.translation import gettext as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.gui.bulk_update import FieldOverrider
from creme.creme_core.models import FieldsConfig

from .. import get_folder_model

Folder = get_folder_model()


class BaseFolderCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pk = self.instance.id
        if pk:
            # TODO: remove direct children too?
            # TODO: would be cool to get 'instance' in limit_choices_to...
            self.fields['parent_folder'].q_filter = ~Q(id=pk)


class ParentFolderOverrider(FieldOverrider):
    field_names = ['parent_folder']

    def formfield(self, instances, user, **kwargs):
        first = instances[0]

        model = type(first)
        model_field = model._meta.get_field(self.field_names[0])
        field = model_field.formfield()
        field.user = user  # TODO: fix in order it works in constructor too

        if len(instances) == 1 and first.pk:
            # TODO: like above -> exclude direct children too?
            field.q_filter = ~Q(id=first.pk)
            field.initial = first.parent_folder_id

        # TODO: get a 'form' argument & use form.fields_configs?
        field.required = FieldsConfig.objects.get_for_model(model).is_field_required(model_field)

        return field

    # TODO: default implementation of post_clean_instance()?
    def post_clean_instance(self, *, instance, value, form):
        setattr(instance, self.field_names[0], value)


def get_merge_form_builder():
    from creme.creme_core.forms.merge import MergeEntitiesBaseForm

    class FolderMergeForm(MergeEntitiesBaseForm):
        # TODO: uncomment & remove the code in init which exclude the field ?
        #      (MergeEntitiesBaseForm has to be a ModelForm...)
        # class Meta(MergeEntitiesBaseForm.Meta):
        #     exclude = ('parent_folder',)

        def __init__(self, entity1, entity2, *args, **kwargs):
            parented = False

            if entity2.already_in_children(entity1.id):
                entity1, entity2 = entity2, entity1
                parented = True

            if str(entity2.uuid) in Folder.not_deletable_UUIDs:
                if str(entity1.uuid) in Folder.not_deletable_UUIDs:
                    raise self.CanNotMergeError(_('Can not merge 2 system Folders.'))

                if parented or entity1.already_in_children(entity2.id):
                    raise self.CanNotMergeError(
                        _(
                            'Can not merge because a child is a system Folder: {folder}'
                        ).format(folder=entity2)
                    )

                entity1, entity2 = entity2, entity1

            super().__init__(entity1, entity2, *args, **kwargs)

            del self.fields['parent_folder']

    return FolderMergeForm
