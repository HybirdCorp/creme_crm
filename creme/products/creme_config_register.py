# -*- coding: utf-8 -*-

from . import models
from .forms import category

to_register = ((models.Category,    'category'),
               (models.SubCategory, 'subcategory', category.SubCategoryForm),
              )
