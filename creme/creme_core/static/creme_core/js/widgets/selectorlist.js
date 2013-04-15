/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.widget.SelectorList = creme.widget.declare('ui-creme-selectorlist', {
    options: {},

    _create: function(element, options, cb, sync)
    {
        var self = this;

        $('div.add ul', element).click(function() {
            self.appendLastSelector(element);
        });

        var value = this.val(element);

        if (creme.object.isempty(value))
        {
            this._update(element);
            value = this.val(element);
        }

        self._updateSelectors(element, self.val(element));

        element.addClass('widget-ready');
        creme.object.invoke(cb, element);
    },

    _buildSelector: function(element)
    {
        var model = this.selectorModel(element).clone();
        return creme.widget.create(model, {}, undefined, true);
    },

    lastSelector: function(element) {
        return $('ul.selectors > li.selector:last > ul > li > .ui-creme-widget', element);
    },

    selectorModel: function(element) {
        return $('.inner-selector-model > .ui-creme-widget', element);
    },

    selectors: function(element) {
        return $('ul.selectors > li.selector > ul > li > .ui-creme-widget', element);
    },

    selector: function(element, index) {
        return $('ul.selectors > li.selector:nth(' + index + ') > ul > li > .ui-creme-widget', element);
    },

    removeSelector: function(element, index)
    {
        var selector = this.selector(element, index);

        selector.creme().destroy();
        selector.parents('li.selector:first').remove();
        this._update(element);

        return selector.length ? selector[0] : undefined;
    },

    appendLastSelector: function(element)
    {
        var last = this.lastSelector(element);
        return this.appendSelector(element, last.creme().isActive() ? last.creme().widget().val() : undefined);
    },

    appendSelector: function(element, value)
    {
        var selector = this._appendSelector(element, value);
        this._update(element);
        return selector.element;
    },

    _appendSelector: function(element, value)
    {
        var self = this;
        var selector_model = this.selectorModel(element).clone();

        if (creme.object.isempty(selector_model))
            return;

        selector_model.css('display', 'hidden');

        var selector_item = $('<li>').addClass('selector');
        var selector_layout = $('<ul>').addClass('ui-layout hbox').css('display', 'block').appendTo(selector_item);

        var delete_button = $('<img/>').attr('src', creme_media_url('images/delete_22.png'))
                                       .attr('alt', gettext("Delete"))
                                       .attr('title', gettext("Delete"))
                                       .attr('style', 'vertical-align:middle;')
                                       .addClass('delete')
                                       .click(function() {
                                            self.removeSelector(selector_item)
                                            selector_item.remove();
                                            self._update(element);
                                        });

        selector_layout.append($('<li>').append(selector_model));
        selector_layout.append($('<li>').append(delete_button));

        $('ul.selectors', element).append(selector_item);

        selector_model.bind('change', function() {
            self._update(element);
        });

        var selector = creme.widget.create(selector_model, {}, function() {
            selector_model.css('display', 'inline');
        }, true);

        if (creme.object.isempty(selector)) {
            selector_item.removeFromParent();
            return;
        }

        selector.val(value);
        return selector;
    },

    _update: function(element)
    {
        var values = creme.widget.values_list(this.selectors(element));
        creme.widget.input(element).val('[' + values.join(',') + ']');
    },

    _updateSelectors: function(element, data)
    {
        var values = creme.widget.cleanval(data, []);

        if (typeof values !== 'object')
            return;

        $('ul.selectors', element).empty();

        for (var i = 0; i < values.length; ++i) {
            this._appendSelector(element, values[i]);
        }
    },

    val: function(element, value)
    {
        if (value === undefined)
            return creme.widget.input(element).val();

        this._updateSelectors(element, value);
        this._update(element);
    }
});
