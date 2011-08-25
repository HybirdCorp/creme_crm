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

    _create: function(element, options) {
        var self = creme.widget.SelectorList;

        $('div.add ul', element).click(function() {
            self.append_selector(element);
        });

        self._update_selectors(element, self.val(element));
        element.addClass('widget-ready');
    },

    _get_selector: function(element, selector) {
        var self = creme.widget.SelectorList;

        if (selector === undefined) {
            var model = $('ul.selectors .selector:last', element);

            if (model === undefined || model === null || model.length === 0) {
                model = $('.inner-selector-model > .ui-creme-widget', element);
            }

            selector = model.data('widget').clone(model);
            selector.data('widget').init(selector);
        }

        return selector;
    },

    append_selector: function(element, selector) {
        var self = creme.widget.SelectorList;

        var selector = self._get_selector(element, selector);
        selector.addClass('selector').attr('style', 'display:inline;');

        var selector_item = $('<ul>').addClass('ui-layout hbox').css('display', 'block');

        var delete_button = $('<img/>').attr('src', creme_media_url('images/delete_22.png'))
                                       .attr('alt', gettext("Delete"))
                                       .attr('title', gettext("Delete"))
                                       .attr('style', 'vertical-align:middle;')
                                       .addClass('delete')
                                       .click(function() {
                                            selector_item.remove();
                                            self._update(element);
                                        });

        selector_item.append($('<li>').append(selector));
        selector_item.append($('<li>').append(delete_button));

        $('ul.selectors', element).append(selector_item);
        self._update(element);

        //console.log('selector', selector);

        selector.bind('change', function() {
            self._update(element);
        });

        return selector;
    },

    _update: function(element) {
        var self = creme.widget.SelectorList;
        var values = creme.widget.val($('ul.selectors .selector', element));
        creme.widget.input(element).val('[' + values.join(',') + ']');
    },

    _update_selectors: function(element, value) {
        var self = creme.widget.SelectorList;
        var values = creme.widget.parseval(value, creme.ajax.json.parse);

        if (values === undefined)
            return;

        $('ul.selectors', element).empty();

        if (values === null)
            return;

        for (var i = 0; i < values.length; ++i) {
            var selector = self.append_selector(element);
            selector.data('widget').val(selector, values[i]);
        }
    },

    val: function(element, value) {
        var self = creme.widget.SelectorList;

        if (value === undefined)
            return creme.widget.input(element).val();

        self._update_selectors(value);
           creme.widget.input(element).val(value);
    }
});
