# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2021 Hybird
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

from typing import Iterable, Iterator, List, Tuple, Union

from django.contrib.contenttypes.models import ContentType
from django.http import Http404


# TODO: python 3.8 '/' arguments
def as_ctype(ct_or_model_or_instance) -> ContentType:
    return (
        ct_or_model_or_instance
        if isinstance(ct_or_model_or_instance, ContentType) else
        ContentType.objects.get_for_model(ct_or_model_or_instance)
    )


def entity_ctypes() -> Iterator[ContentType]:
    "Generator which yields ContentType instances corresponding to registered entity models."
    from ..registry import creme_registry
    return map(
        ContentType.objects.get_for_model,
        creme_registry.iter_entity_models(),
    )


def get_ctype_or_404(ct_id: Union[int, str]) -> ContentType:
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


def ctype_choices(ctypes: Iterable[ContentType]) -> List[Tuple[int, str]]:
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
