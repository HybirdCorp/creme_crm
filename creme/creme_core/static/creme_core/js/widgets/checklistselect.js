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

        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._grouped = creme.object.isTrue(options.grouped) || element.is('[grouped]');
        this._converter = options.datatype === 'json' ? creme.utils.JSON.decoder({}) : null;

        this._initializeController(element, options);

        $('.checklist-check-all', element).click(function() {self.selectAll(element);});
        $('.checklist-check-none', element).click(function() {self.unselectAll(element);});
        $('.checklist-filter', element).bind('propertychange keyup input paste', function() {self._updateViewFilter(element, $(this).val().toLowerCase());});

        $('.checkbox-field input[type="checkbox"]', element).live('click', function() {
            self._delegate(element).val(self.selected(element));
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

    _delegate: function(element) {
        return $('select.ui-creme-input', element);
    },

    _initializeController: function(element, options)
    {
        var self = this;
        var disabled = !this._enabled;
        var input = this._delegate(element);
        var content = this.content(element);

        var renderer = this._grouped ? new creme.model.CheckGroupListRenderer() : new creme.model.CheckListRenderer();
        var controller = this._controller = new creme.model.CollectionController(this._backend);

        var choices = this._grouped ? creme.model.ChoiceGroupRenderer.parse(input) : creme.model.ChoiceRenderer.parse(input);

        renderer.converter(this._converter);

        controller.renderer(renderer)
                  .target(content)
                  .model(new creme.model.Array(choices))
                  .redraw();

        content.addClass('ie-checkbox-fallback')

        if ($.browser.msie && !this._grouped)
        {
            var layout = new creme.layout.ColumnSortLayout();
            var column_width = content.get()[0].currentStyle['column-width'] || '200px';

            content.addClass('ie-layout-fallback')

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
        var value = value.map(function(item) {return $.toJSON(item);});

        if (previous === value)
            return this;

        if (input)
        {
            input.val(value);
            element.change();
        }

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
        return $('.checklist-content input[type="checkbox"]:checked', element).map(function() {
            return $(this).val();
        }).get();
    },

    selectAll: function(element)
    {
        $('.checklist-content input[type="checkbox"]', element).each(function() {
            $(this).get()[0].checked = true;
        });

        this._delegate(element).val(this.selected(element));
        return this;
    },

    unselectAll: function(element)
    {
        $('.checklist-content input[type="checkbox"]', element).each(function() {
            $(this).get()[0].checked = false;
        });

        this._delegate(element).val(this.selected(element));
        return this;
    }
});

