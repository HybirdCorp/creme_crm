# -*- coding: utf-8 -*-


from django import template

register = template.Library()

@register.filter(name="latexnewline")
def latexnewline(x):
    return x.replace("\n","\\newline ")