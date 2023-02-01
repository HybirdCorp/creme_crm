################################################################################
#
# Copyright (c) 2009-2023 Hybird
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

from __future__ import annotations

from typing import Container, Iterable, Iterator

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.http import Http404


# def as_ctype(ct_or_model_or_instance) -> ContentType:
#     return (
#         ct_or_model_or_instance
#         if isinstance(ct_or_model_or_instance, ContentType) else
#         ContentType.objects.get_for_model(ct_or_model_or_instance)
#     )
def as_ctype(value: ContentType | type[Model] | Model, /) -> ContentType:
    return (
        value
        if isinstance(value, ContentType) else
        ContentType.objects.get_for_model(value)
    )


def entity_ctypes(app_labels: Container[str] | None = None) -> Iterator[ContentType]:
    """Generator which yields ContentType instances corresponding to registered
     entity models.
    @param app_labels: If None is given, all the registered models are yielded.
           If a container of app labels is given, only models related to these
           apps are yielded.
    """
    from ..registry import creme_registry
    return map(
        ContentType.objects.get_for_model,
        creme_registry.iter_entity_models(app_labels=app_labels),
    )


def get_ctype_or_404(ct_id: int | str) -> ContentType:
    """Retrieve a ContentType by its ID.
    @param ct_id: ID of the wanted ContentType instance (int or string).
    @return: ContentType instance.
    @raise: Http404 Exception if the ContentType does not exist.
    """
    try:
        ct = ContentType.objects.get_for_id(ct_id)
    except (ValueError, ContentType.DoesNotExist) as e:
        raise Http404(f'No content type with this id: {ct_id}') from e

    return ct


def ctype_choices(ctypes: Iterable[ContentType]) -> list[tuple[int, str]]:
    """ Build a choices list (useful for form ChoiceField for example) for ContentTypes.
    Labels are localized, & choices are sorted by labels.
    @param ctypes: Iterable of ContentTypes.
    @return: A list of tuples.
    """
    from .unicode_collation import collator
    choices = [(ct.id, str(ct)) for ct in ctypes]

    sort_key = collator.sort_key
    choices.sort(key=lambda k: sort_key(k[1]))

    return choices
