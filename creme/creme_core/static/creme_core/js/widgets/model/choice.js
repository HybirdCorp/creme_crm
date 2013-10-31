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
            value = new creme.utils.JSON().encode(data.value)

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
    var values = element.val();
    values = element.is('[multiple]') ? (values || []) : [values];

    return $('option', element).map(function() {
        var option = $(this);
        var option_value = option.attr('value');

        return {
            label:    option.html(), 
            value:    Object.isFunc(converter) ? converter(option_value) : option_value,
            disabled: option.is('[disabled]'), 
            selected: values.indexOf(option_value) !== -1,
            visible:  true,
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
            value = new creme.utils.JSON().encode(data.value)

        item.attr('value', value)
            .toggleAttr('disabled', data.disabled === true)
            .toggleAttr('selected', data.selected === true)
            .toggleAttr('tags', data.tags, (data.tags || []).join(' '))
            .html(data.label);
    },
});

creme.model.ChoiceGroupRenderer.parse = function(element, converter) {
    var values = element.val();
    values = element.is('[multiple]') ? (values || []) : [values]; 

    return $('option', element).map(function() {
        var option = $(this);
        var option_value = option.attr('value');
        var option_group = option.parent();

        return {
            group:    (option_group && option_group.is('optgroup')) ? option_group.attr('label') : undefined,
            label:    option.html(),
            value:    Object.isFunc(converter) ? converter(option_value) : option_value,
            disabled: option.is('[disabled]'),
            selected: values.indexOf(option_value) !== -1,
            visible:  true,
            tags:     option.is('[tags]') && option.attr('tags') ? option.attr('tags').split(' ') : []
        };
    }).get();
}


creme.model.CheckListRenderer = creme.model.ListRenderer.sub({
    _init_: function(options)
    {
        var options = $.extend({itemtag: 'li', disabled: false}, options || {});

        this._super_(creme.model.ListRenderer, '_init_');
        this._itemtag = options.itemtag;
        this._disabled = options.disabled;
    },

    disabled: function(disabled) {
        return Object.property(this, '_disabled', disabled);
    },

    createItem: function(target, before, data, index)
    {
        var item = $('<%s class="checkbox-field"><input type="checkbox"/><span class="checkbox-label"></span></%s>'.format(this._itemtag));
        this.updateItem(target, item, data, undefined, index);
        return item;
    },

    updateItem: function(target, item, data, previous, index)
    {
        var value = Object.isNone(data.value) ? '' : data.value;
        var checkbox = $('input[type="checkbox"]', item);

        if (typeof data.value === 'object')
            value = new creme.utils.JSON().encode(data.value)

        var disabled = data.disabled || this._disabled;

        checkbox.toggleAttr('disabled', data.disabled || disabled)
                .attr('value', value)
                .data('checklist-item', {data: data, index:index})

        checkbox.get()[0].checked = data.selected;

        $('.checkbox-label', item).toggleAttr('disabled', disabled)
                                  .html(data.label);

        item.toggleAttr('tags', data.tags, (data.tags || []).join(' '))
            .toggleClass('hidden', !data.visible)
            .toggleClass('disabled', disabled);
    },

    items: function(target) {
        return $('.checkbox-field', target);
    },

    converter: function(converter) {
        return Object.property(this, '_converter', converter);
    },

    parseItem: function(target, item, index)
    {
        var converter = this._converter;
        var input = $('input[type="checkbox"]', item);
        var label = $('.checkbox-label', item);
        var value = input.attr('value');

        return {
            label:    label.html(), 
            value:    Object.isFunc(converter) ? converter(value) : value,
            disabled: input.is('[disabled]') || target.is('[disabled]'), 
            selected: input.is(':checked'),
            tags:     input.is('[tags]') ? input.attr('tags').split(' ') : [],
            visible:  true
        };
    },

    parse: function(target)
    {
        var self = this;

        this._itemtag = this.items(target).first().prop('tagName') || this._itemtag;

        return this.items(target).map(function(index) {
            return self.parseItem(target, $(this), index);
        }).get();
    }
});

creme.model.CheckGroupListRenderer = creme.model.CheckListRenderer.sub({
    _init_: function(options)
    {
        var options = $.extend({grouptag: 'ul'}, options || {});

        this._super_(creme.model.CheckListRenderer, '_init_', options);
        this._grouptag = options.grouptag;
    },

    insertGroup: function(target, before, groupname)
    {
        var group = $('.checkbox-group[label="' + groupname + '"]', target);

        if (group && group.length) {
            return group;
        }

        group = $('<' + this._grouptag + '>').addClass('checkbox-group')
                                             .attr('label', groupname)
                                             .append($('<li>').addClass('checkbox-group-header').html(groupname));

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
                before = $('.checkbox-field:first', group);
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

        if (group && this.items(group).length < 1)
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

            if (prev_group && (this.items(prev_group).length) < 1)
                prev_group.remove();
        }

        return this._super_(creme.model.CheckListRenderer, 'updateItem', target, item, data, previous, index);
    },

    parseItem: function(target, item, index)
    {
        var data = this._super_(creme.model.CheckListRenderer, 'parseItem', target, item, index);
        var checkbox_group = item.parent();

        data.group = (checkbox_group && checkbox_group.is('.checkbox-group')) ? option_group.attr('label') : undefined;
        return data;
    }
});
