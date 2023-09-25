################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023  Hybird
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

# TODO: remove
from json import dumps as json_dump
from json import loads as json_load

from creme.creme_core.core.paginator import FlowPaginator


def _convert_filter_conditions(*, apps, model, ctype, old_field: str, new_field: str):
    from creme.creme_core.core.entity_filter import condition_handler

    # TODO: manage date field
    type_id = condition_handler.RegularFieldConditionHandler.type_id

    # TODO: myfk__....

    apps.get_model('creme_core', 'EntityFilterCondition').objects.filter(
        filter__entity_type=ctype, type=type_id, name=old_field,
    ).update(name=new_field)


# TODO: wait for JSONField in HistoryLine
def _convert_history_lines(*, apps, model, ctype, old_field: str, new_field: str):
    TYPE_EDITION = 2

    def new_ids(model, old_ids):
        for old_id in old_ids:
            instance = model.objects.filter(old_id=old_id).first()
            yield 0 if instance is None else instance.id

    for page in FlowPaginator(
        queryset=apps.get_model('creme_core', 'HistoryLine').objects.filter(
            type=TYPE_EDITION, entity_ctype=ctype,
        ).filter(value__contains=f'["{new_field}"'),
        key='id',
        per_page=256,
    ).pages():
        for hline in page.object_list:
            # NB: new_field could be the name of the entity...
            save = False
            # NB: format is :
            #     ["My entity", ["field1", "old value", "new_value"], ["field2", ...], ...]
            value = json_load(hline.value)  # TODO: remove json_load

            modifications = []
            for old_mod in value[1:]:
                field_name = old_mod[0]
                if field_name == old_field:
                    modifications.append([new_field, *old_mod[1:]])
                    save = True
                else:
                    modifications.append(old_mod)

            if save:
                hline.value = json_dump([value[0], *modifications])
                hline.save()


processors = [
    _convert_filter_conditions,
    _convert_history_lines,
    # TODO: complete
    # TODO: insert from reports in migration mode
]


def post_entity_field_renaming(*, apps,
                               app_label: str, model_name: str,
                               old_field: str, new_field: str,
                               ):
    ctype = apps.get_model('contenttypes', 'ContentType').objects.filter(
        app_label=app_label, model=model_name.lower(),
    ).first()
    if ctype is None:
        return

    model = apps.get_model(app_label, model_name)

    for processor in processors:
        processor(
            apps=apps, model=model, ctype=ctype, old_field=old_field, new_field=new_field,
        )
