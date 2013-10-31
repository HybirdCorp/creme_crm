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

creme.widget = creme.widget || {};

creme.widget.CheckListSelect = creme.widget.declare('ui-creme-checklistselect', {
    options: {
        datatype: 'string',
        grouped: false
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;

        this._grouped = creme.object.isTrue(options.grouped) || element.is('[grouped]');
        this._converter = options.datatype === 'json' ? creme.utils.JSON.decoder({}) : null;

        this.disabled(element, creme.object.isTrue(options.disabled) || element.is('[disabled]'));

        this._initializeController(element, options);

        $('.checklist-check-all:not([disabled])', element).click(function() {
            if (!this._disabled) self.selectAll(element);
        });

        $('.checklist-check-none:not([disabled])', element).click(function() {
            if (!this._disabled) self.unselectAll(element);
        });

        $('.checklist-filter', element).bind('propertychange keyup input paste', function() {
            self._updateViewFilter(element, $(this).val().toLowerCase());
        });

        $('.checkbox-field input[type="checkbox"]', element).bind('click change', function() {
            $(this).data('checklist-item').data.selected = $(this).get()[0].checked;
            self._updateDelegate(element);
        });

        element.addClass('widget-ready');
    },

    _updateViewFilter: function(element, filter)
    {
        var isfiltered = !Object.isEmpty(filter);
        var content = this.content(element);
        var items = $('.checkbox-field', content);
        var counter = $('.checklist-counter', element);

        content.toggleClass('filtered', isfiltered);

        items.each(function() {
            var accepted = $('.checkbox-label', this).html().toLowerCase().indexOf(filter) !== -1;
            $(this).toggleClass('hilighted', accepted);
        });

        var hilighted_count = $('.checkbox-field.hilighted', content).length

        counter.toggleClass('filtered', isfiltered)
               .html(ngettext('%d result of %d', '%d results of %d', hilighted_count).format(hilighted_count, items.length));
    },

    _updateViewSelection: function(element)
    {
        var selections = this.val(element) || [];
        var controller = this._controller;

        controller.model().each(function(item, index) {
            var next = selections.indexOf(item.value) !== -1;

            if (item.selected !== next) {
                item.selected = next;
                controller.model().set(item, index)
            }
        });
    },

    _updateDelegate: function(element)
    {
        this._delegate(element).val(this.selected(element));
        element.change();
    },

    _delegate: function(element) {
        return $('select.ui-creme-input', element);
    },

    _initializeController: function(element, options)
    {
        var self = this;
        var disabled = this.disabled(element);
        var input = this._delegate(element);
        var content = this.content(element).addClass('ie-checkbox-fallback');

        var renderer = this._grouped ? new creme.model.CheckGroupListRenderer() : new creme.model.CheckListRenderer();
        var controller = this._controller = new creme.model.CollectionController(this._backend);

        var choices = this._grouped ? creme.model.ChoiceGroupRenderer.parse(input) : creme.model.ChoiceRenderer.parse(input);

        renderer.converter(this._converter)
                .disabled(disabled);

        controller.renderer(renderer)
                  .target(content)
                  .model(new creme.model.Array(choices))
                  .redraw();

        input.bind('change', function() {self._updateViewSelection(element);});

        if ($.browser.msie && !this._grouped)
        {
            var layout = new creme.layout.ColumnSortLayout();
            var column_width = content.get()[0].currentStyle['column-width'] || '200px';

            content.addClass('ie-layout-fallback');

            layout.comparator(function(a, b) {
                                  return $('.checkbox-label', a).html().localeCompare($('.checkbox-label', b).html());
                              })
                  .columns(column_width)
                  .resizable(true)
                  .bind(content)
                  .layout();
        }

        //this._layout.columns(3).resizable(true).bind(content).layout();
    },

    disabled: function(element, disabled)
    {
        if (disabled === undefined)
            return this._disabled;

        element.toggleAttr('disabled', disabled);
        this._disabled = disabled;

        $('.checklist-check-all, .checklist-check-none, .checklist-filter', element).toggleAttr('disabled', disabled);

        if (this._controller) {
            this._controller.renderer().disabled(disabled);
            this._controller.redraw();
        }

        return this;
    },

    content: function(element)
    {
        var content = $('.checklist-content', element);
        return content.length === 0 ? element : content;
    },

    dependencies: function(element) {
        return [];
    },

    reload: function(element, data, cb, error_cb, sync) {
        return this;
    },

    update: function(element, data) {
    },

    model: function(element) {
        return this._controller.model();
    },

    val: function(element, value)
    {
        var input = this._delegate(element);

        if (value === undefined) {
            return input.val();
        }

        var previous = this.val(element);
        var selections = Object.isType(value, 'string') ? new creme.utils.JSON().decode(value, []) : value;
        var value = value.map(function(item) {return typeof item !== 'string' ? $.toJSON(item) : item;});

        if (previous === value)
            return this;

        if (input) {
            input.val(value).change();
        }

        element.change();
        return this;
    },

    cleanedval: function(element)
    {
        return this.val(element).map(function(value) {
            creme.utils.converters.convert('string', this.options.datatype.toLowerCase(), value, value);
        });
    },

    reset: function(element) {
        this.unselectAll(element);
    },

    selected: function(element) {
        return $('.checkbox-field input[type="checkbox"]:checked', element).map(function() {
            return $(this).val();
        }).get();
    },

    selectAll: function(element)
    {
        $('.checkbox-field input[type="checkbox"]:not([disabled])', element).each(function() {
            $(this).get()[0].checked = true;
        });

        this._controller.model().where(function(item) {return !item.disabled})
                                .forEach(function(item) {item.selected = true;});

        this._updateDelegate(element);
        return this;
    },

    unselectAll: function(element)
    {
        $('.checkbox-field input[type="checkbox"]', element).each(function() {
            $(this).get()[0].checked = false;
        });

        this._controller.model().where(function(item) {return !item.disabled})
                                .forEach(function(item) {item.selected = false;});

        this._updateDelegate(element);
        return this;
    }
});

