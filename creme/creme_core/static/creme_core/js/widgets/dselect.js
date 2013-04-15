/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

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

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        url: '',
        backend: new creme.ajax.Backend({dataType:'json', sync:true}),
        datatype: 'string',
        multiple: undefined,
        sortable: undefined,
        autocomplete: undefined,
        'autocomplete-options': '',
    },

    _create: function(element, options, cb, sync)
    {
        this._initial = element.html();
        this._url = new creme.string.Template(options.url);
        this._fill(element, this.url(element), cb, undefined, sync);
        this._autocomplete = this._init_autocomplete(element, options)
    },

    _init_autocomplete: function(element, options)
    {
        if (options.autocomplete === undefined)
            return;

        try {
            chosen_options = options['autocomplete-options'] || '';
            chosen_options = chosen_options.length ? creme.object.build_callback(chosen_options)() : {};
        } catch(e) {
            chosen_options = {};
        }

        chosen_options = $.extend({
            multiple: options.multiple !== undefined,
            sortable: options.sortable !== undefined,
        }, chosen_options)

        var component = new creme.widget.component.Chosen(chosen_options);
        component.activate(element);

        return component;
    },

    _update_disabled_state: function(element) {
        ($('option', element).length > 1) ? element.removeAttr('disabled') : element.attr('disabled', 'disabled');
    },

    url: function(element) {
        return this._url.render();
    },

    dependencies: function(element) {
        return this._url.tags();
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        this._url.update(data);
        this._fill(element, this.url(element), cb, error_cb, sync);
    },

    update: function(element, data)
    {
        var self = this;
        data = creme.widget.parseval(data, creme.ajax.json.parse);

        if (typeof data !== 'object' || data === null)
           return;

        var selected = data['value'];
        var added_items = data['added'] || [];
        var removed_items = data['removed'] || [];

        removed_items.forEach(function(item) {
            $('option[value="' + item + '"]', element).detach();
        });

        added_items.forEach(function(item) {
            element.append($('<option/>').val(item[0]).text(item[1]));
        });

        self.val(element, selected);
        self._update_disabled_state(element);
    },

    _fill_begin: function(element) {
        element.removeClass('widget-ready');
    },

    _fill_end: function(element, old) {
        element.addClass('widget-ready');
        this._triggerchanged(element, old);
    },

    _triggerchanged: function(element, old)
    {
        if (this.val(element) !== old) {
            // Chrome behaviour (bug ?) : select value is not updated if disabled.
            // so enable it before change value !
            element.removeAttr('disabled');
            element.change();

            if (this._autocomplete) {
                this._autocomplete.refresh();
            }
        }

        this._update_disabled_state(element);
    },

    _staticfill: function(element, data) {
        creme.forms.Select.fill(element, data);
    },

    _ajaxfill: function(element, url, cb, error_cb, sync)
    {
        var self = this;
        var old = this.val(element)

        if (creme.object.isempty(url))
        {
            element.empty();
            element.html(self._initial);
            self._fill_end(element, old);
            creme.object.invoke(error_cb, element, new creme.ajax.AjaxResponse('404', ''));
            return;
        }

        this.options.backend.get(url, {fields:['id', 'unicode']},
                                 function(data) {
                                     self._staticfill(element, data);
                                     self._fill_end(element, old);
                                     creme.object.invoke(cb, element);
                                 },
                                 function(data, error) {
                                     element.empty();
                                     element.html(self._initial);
                                     self._fill_end(element, old);
                                     creme.object.invoke(error_cb, element, error);
                                 },
                                 {sync:sync});
    },

    _fill: function(element, data, cb, error_cb, sync)
    {
        var self = this;

        if (creme.object.isnone(data) === true) {
            creme.object.invoke(cb, element);
            return;
        }

        self._fill_begin(element);

        if (typeof data === 'string') {
            self._ajaxfill(element, data, cb, error_cb, sync);
            return;
        }

        if (typeof data === 'array') {
            self._staticfill(element, data);
        }

        self._fill_end(element);
        creme.object.invoke(cb, element);
    },

    val: function(element, value)
    {
        if (value === undefined)
            return element.val();

        var old = element.val();

        if (typeof value !== 'string')
            value = $.toJSON(value);

        if (this.choice(element, value) === undefined) {
            this.selectfirst(element);
        } else {
            element.val(value);
        }

        this._triggerchanged(element, undefined);
    },

    cleanedval: function(element)
    {
        var value = this.val(element);

        if (this.options.datatype == 'string')
            return value;

        return creme.widget.cleanval(value, value);
    },

    reset: function(element) {
        this.selectfirst(element);
    },

    selectfirst: function(element) {
        this.val(element, this.firstchoice(element));
    },

    firstchoice: function(element)
    {
        return this._querychoices(element).attr('value');
    },

    _querychoices: function(element, key)
    {
        return $('option' + (key ? '[value="' + key + '"]' : ''), element).filter(function() {
            return $(this).parents('select:first').is(element);
        });
    },

    _querygroups: function(element, key)
    {
        return $('optgroup' + (key ? '[value="' + key + '"]' : ''), element).filter(function() {
            return $(this).parents('select:first').is(element);
        });
    },

    choice: function(element, key)
    {
        if (creme.object.isempty(key) === true)
            return;

        return [key, this._querychoices(element, key).text()];
    },

    choices: function(element)
    {
        var choices = [];

        this._querychoices(element).each(function() {
            choices.push([$(this).attr('value'), $(this).text()]);
        });

        return choices;
    },

    groups: function(element)
    {
        var groups = [];

        this._querygroups(element).each(function() {
            return groups.push($(this).attr('label'));
        });

        return groups;
    },

    selected: function(element) {
        return this.choice(element, this.val(element));
    }
});

//(function($) {
//    $.widget("ui.dselect", creme.widget.dselect);
//})(jQuery);
