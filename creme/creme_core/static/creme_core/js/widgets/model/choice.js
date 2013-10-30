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
            tags:     option.is('[tags]') && option.attr('tags') ? option.attr('tags').split(' ') : []
        };
    }).get();
}


creme.model.ChoiceGroupRenderer = creme.model.ChoiceRenderer.sub({
    insertGroup: function(target, before, groupname)
    {
        var group = $('optgroup[label="' + groupname + '"]', target);

        if (group && group.length) {
            return group;
        }

        group = $('<optgroup label="' + groupname + '">');

        if (before && before.length) {
            before.parent().before(group);
        } else {
            target.append(group);
        }

        return group;
    },

    insertItem: function(target, before, data, index)
    {
        var group = target;
        var previous_groupname = before && before.length ? before.parent().attr('label') : undefined;
        var next_groupname = data.group;

        if (next_groupname) {
            group = this.insertGroup(target, before, next_groupname);
        }

        if (before && before.length)
        {
            if (next_groupname && previous_groupname !== next_groupname) {
                before = $('option:first', group);
            }

            before.before(this.createItem(target, before, data, index));
        } else {
            group.append(this.createItem(target, before, data, index));
        }
    },

    removeItem: function(target, item, data, index)
    {
        var group = data.group ? item.parent() : undefined;

        item.remove();

        if (group && $('option', group).length < 1)
            group.remove();
    },

    updateItem: function(target, item, data, previous, index)
    {
        var group = target;
        var prev_group = item.parent();

        var previous_groupname = previous ? previous.group : undefined;
        var next_groupname = data.group;

        if (next_groupname) {
            group = this.insertGroup(target, item.next(), next_groupname);
        }

        if (previous_groupname !== next_groupname)
        {
            item.remove();
            group.append(item);

            if (prev_group && ($('option', prev_group).length) < 1)
                prev_group.remove();
        }

        var value = Object.isNone(data.value) ? '' : data.value;

        if (typeof data.value === 'object')
            value = new creme.object.JSON().encode(data.value)

        item.attr('value', value)
            .toggleAttr('disabled', data.disabled === true)
            .toggleAttr('selected', data.selected === true)
            .toggleAttr('tags', data.tags, (data.tags || []).join(' '))
            .html(data.label);
    },
});

creme.model.ChoiceGroupRenderer.parse = function(element) {
    return $('option', element).map(function() {
        var option = $(this);
        return {
            group:    (option.parent() && option.parent().is('optgroup')) ? option.parent().attr('label') : undefined,
            label:    option.html(),
            value:    option.attr('value'),
            disabled: option.is('[disabled]'),
            selected: element.val() === option.attr('value'),
            tags:     option.is('[tags]') && option.attr('tags') ? option.attr('tags').split(' ') : []
        };
    }).get();
}
