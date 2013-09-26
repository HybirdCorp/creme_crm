/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

creme.model = creme.model || {};

creme.model.ChoiceRenderer = creme.model.ListRenderer.sub({
    createItem: function(target, before, data, index)
    {
        var item = $('<option>');
        this.updateItem(target, item, data, undefined, index);
        return item;
    },

    updateItem: function(target, item, data, previous, index)
    {
        var value = Object.isNone(data.value) ? '' : data.value;

        if (typeof data.value === 'object')
            value = new creme.object.JSON().encode(data.value)

        item.attr('value', value)
            .toggleAttr('disabled', data.disabled === true)
            .toggleAttr('selected', data.selected === true)
            .toggleAttr('tags', data.tags, (data.tags || []).join(' '))
            .html(data.label);
    },

    items: function(target) {
        return $('option', target);
    }
});

creme.model.ChoiceRenderer.parse = function(element, converter) {
    return $('option', element).map(function() {
        var option = $(this);
        var value = option.attr('value');

        return {
            label:    option.html(), 
            value:    Object.isFunc(converter) ? converter(value) : value,
            disabled: option.is('[disabled]'), 
            selected: element.val() === option.attr('value'),
            tags:     option.is('[tags]') ? option.attr('tags').split(' ') : []
        };
    }).get();
}
