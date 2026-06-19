################################################################################
#
# Copyright (c) 2013-2026 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

from django.apps import apps
from django.db.models import Model

from ..signals import pre_replace_related


# In some (few) cases when the foreignkey is defined with a string AND the apps
# are not loaded in the right order, the model-field instance can have an
# unresolved related model as a string...
def safe_model(model: type[Model] | str) -> type[Model]:
    """@param model: If a string is given, it must be like 'my_app.MyModel'."""
    return apps.get_model(model) if isinstance(model, str) else model


def update_model_instance(obj: Model, **fields) -> bool:
    """Update the field values of an instance, and save it only if it has changed.
    @param obj: Instance to update
    @param fields: Field names & (new) values as a dictionary.
    @return: A boolean indicating if a change has been detected (& so, saved).
    """
    save = False

    for f_name, f_value in fields.items():
        if getattr(obj, f_name) != f_value:
            setattr(obj, f_name, f_value)
            save = True

    # TODO: save only modified fields ?
    if save:
        obj.save()

    return save


# TODO: unit test
def replace_related_object(old_instance: Model, new_instance: Model) -> None:
    """Replace the references to an instance by references to another one."""
    from ..models import HistoryLine

    pre_replace_related.send(
        sender=old_instance.__class__,
        old_instance=old_instance,
        new_instance=new_instance,
    )  # send_robust() ??

    meta = old_instance._meta
    mark = HistoryLine.mark_as_reassigned

    for rel_objects in (f for f in meta.get_fields() if f.one_to_many):
        field_name = rel_objects.field.name

        for rel_object in getattr(old_instance, rel_objects.get_accessor_name()).all():
            mark(
                rel_object,
                old_reference=old_instance,
                new_reference=new_instance,
                field_name=field_name,
            )
            setattr(rel_object, field_name, new_instance)
            rel_object.save()

    for rel_objects in (
        f
        for f in meta.get_fields(include_hidden=True)
        if f.many_to_many and f.auto_created
    ):
        field_name = rel_objects.field.name

        # TODO: use old_instance.get_m2m_values(...)?
        for rel_object in getattr(old_instance, rel_objects.get_accessor_name()).all():
            m2m_mngr = getattr(rel_object, field_name)
            m2m_mngr.add(new_instance)
            m2m_mngr.remove(old_instance)
