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

creme.widget.PolymorphicSelect = creme.widget.declare('ui-creme-polymorphicselect', {
    options: {
        type: null
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;

        this._selector_change = function() {
            self._update(element);
        };

        var value = creme.widget.cleanval(this.val(element), {type: options.type, value: ''});

        this._selectorType = null;
        this._updateSelector(element, value);
        creme.object.invoke(cb, element);
    },

    _updateSelector: function(element, value)
    {
        var previous = creme.widget.cleanval(this.val(element), {type: this._selectorType, value: ''});
        var next = creme.widget.cleanval(value, {type: this._selectorType, value: ''});

        if (creme.object.isnone(next.type))
            next.type = previous.type;

        //console.log("_update_selector > value:", value, ", previous:", previous, ", val:", this.val(element), ", next:", next);

        element.removeClass('widget-ready');
        this._toggleSelector(element, next.type, next.value, {});
        element.addClass('widget-ready');

//        console.log("_update_selector > value  >", value, ' (type="' + (typeof value) + '")');
//        console.log("                 > real   >", this.val(element));
//        console.log("                 > widget >", this.selector(element).attr('input-type'));
    },

    _update: function(element)
    {
        var data = {type: this.selectorType(element),
                    value: this.selectorValue(element)};

//        console.log("_update > data:", data);
        creme.widget.input(element).val($.toJSON(data));
    },

    _toggleSelector: function(element, type, value, options)
    {
         var current = this.selector(element).creme().widget();

         // already active selector, set value and get out !
         if (!creme.object.isnone(this._selectorType) && this._selectorType === type) {
             current.val(value);
             return;
         }

         var next = this._createSelector(element, type, options);

         // not such valid selector of this type, set value and get out !
         if (creme.object.isnone(next))
         {
             if (!creme.object.isempty(current)) {
                 current.val(value);
             } else {
                 creme.widget.input(element).val($.toJSON({type: this._selectorType, value: value}));
             }

             return;
         }

         if (!creme.object.isempty(current))
         {
             current.element.unbind('change', this._widget_change);
             current.element.remove();
             current.destroy();
         }

         this._selectorType = type;

         next.element.addClass("active-selector").css('display', 'inline')
                                                 .attr('input-type', type);
         next.element.bind('change', this._selector_change);
         element.append(next.element);

         // force value in new selector and get the result
         next.val(value);
    },

    _createSelector: function(element, type, options)
    {
        var model = this.selectorModel(element, type);

        if (!creme.object.isempty(model))
             return creme.widget.create(model.clone(), options, undefined, true);
    },

    selectorType: function(element) {
        return this._selectorType;
    },

    selectorValue: function(element)
    {
        var selector = this.selector(element).creme().widget();
        var value = selector !== undefined ? selector.val() : null;
        return creme.widget.cleanval(value, value);
    },

    selector: function(element) {
        return $('.ui-creme-widget.active-selector', element);
    },

    selectorModel: function(element, type)
    {
        if (creme.object.isnone(type))
            return;

        var model = $('.selector-model li[input-type="' + type + '"] > .ui-creme-widget', element);

        if (creme.object.isempty(model))
             model = this.defaultSelectorModel(element);

        return model;
    },

    defaultSelectorModel: function(element) {
        return $('.selector-model li.default:first > .ui-creme-widget', element);
    },

    selectorModelList: function(element) {
        return $('.selector-model li > .ui-creme-widget', element);
    },

    dependencies: function(element) {
        return ['operator'];
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        if (creme.object.isempty(data))
            return;

        var values = creme.widget.cleanval(this.val(element), {type: this._selectorType, value: null});

        if (typeof data === 'string')
            values.type = data;

        if (typeof data === 'object')
            values['type'] = data.operator;

        this.val(element, values);
        creme.object.invoke(cb, element);
        //console.log("pselect.reload > value >", this.val(element));
    },

    reset: function(element) {
        this.val(element, {type: this.options.type, value: ''});
    },

    val: function(element, value)
    {
        if (value === undefined)
            return creme.widget.input(element).val();

        //console.log("pselect.val >", element, "new=" + $.toJSON(value), "old=" + creme.widget.input(element).val());
        this._updateSelector(element, value);
        element.trigger('change');
    }
});
