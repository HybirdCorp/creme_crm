/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

(function($) {
"use strict";

creme.widget.EntitySelectorMode = {
    MULTIPLE: 'multiple',
    SINGLE: 'single'
};

creme.widget.EntitySelector = creme.widget.declare('ui-creme-entityselector', {

    options: {
        popupURL: '',
        popupSelection: creme.widget.EntitySelectorMode.SINGLE,
        labelURL: '',
        label: gettext('Select'),
        qfilter: '',
        backend: undefined
    },

    _create: function(element, options, cb, sync) {
        var self = this;

        this._backend = options.backend || creme.ajax.defaultCacheBackend();
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');

        if (!this._enabled) {
            $(element).attr('disabled', '');
            $('button', element).attr('disabled', '');
        }

        $(element).on('click', function() {
            if (self._enabled) {
                self._select(element);
            }
        });

        $(element).on('action', function(e, action, listeners) {
            if (action === 'select') {
                self._select(element, listeners);
            }
        });

        creme.widget.input(element).on('invalid html5-invalid', function() {
            $('button', element).toggleClass('is-field-invalid', $(this).is(':invalid'));
        });

        this._popupURL = new creme.utils.Template(options.popupURL, {
                                                       qfilter: options.qfilter,
                                                       selection: options.popupSelection
                                                   });

        this._reloadLabel(element, cb, undefined, sync);
        element.addClass('widget-ready');
    },

    dependencies: function(element) {
        return this._popupURL.tags();
    },

    reload: function(element, data, cb, error_cb, sync) {
        this._popupURL.update(data);
        this.val(element, null);
        creme.object.invoke(cb, element);
    },

    update: function(element, data) {
        data = _.isString(data) ? _.cleanJSON(data) : data;

        if (!Object.isNone(data)) {
            this.val(element, data['value']);
        }
    },

    _select: function(element, listeners) {
        listeners = listeners || {};

        var self = this;
        var multiple = this.isMultiple(element);
        var url = this.popupURL(element);

        var selector = new creme.lv_widget.ListViewDialog({
                                               url: url,
                                               selectionMode: multiple ? 'multiple' : 'single',
                                               closeOnEscape: true
                                           });

        selector.onValidate(function(event, data) {
                     self.val(element, data[0]);

                     if (data.length > 1) {
                         $(element).trigger('change-multiple', [data]);
                     }

                     creme.object.invoke(listeners.done, 'done', element, data);
                 })
                .onClose(function() {
                     creme.object.invoke(listeners.cancel, 'cancel');
                 })
                .open();
    },

    _reloadLabel: function(element, on_success, on_error, sync) {
        var options = this.options;
        var button = $('button', element);
        var value = creme.widget.input(element).val();

        if (Object.isEmpty(value) === true) {
            button.text(options.label);
            creme.object.invoke(on_success, element);
            return;
        }

        var url = (options.labelURL || '').template({id: value});
        var default_label = gettext('Entity #%s (not viewable)').format(value);

        this._backend.get(url, {fields: ['summary']},
                          function(data, status) {
                              try {
                                  button.html(data[0][0] || default_label);
                              } catch (e) {
                                  button.html(default_label);
                              }

                              creme.object.invoke(on_success, element, data);
                          },
                          function(data, error) {
                              button.html(default_label);
                              creme.object.invoke(on_error, element, error);
                          },
                          {dataType: 'json', sync: sync});
    },

    isMultiple: function(element, value) {
        if (value === undefined) {
            return this._popupURL.parameters().selection === creme.widget.EntitySelectorMode.MULTIPLE;
        }

        value = value ? creme.widget.EntitySelectorMode.MULTIPLE : creme.widget.EntitySelectorMode.SINGLE;
        this._popupURL.update({selection: value});
    },

    parentSelectorList: function(element) {
        return element.parents('.ui-creme-selectorlist').first();
    },

    qfilter: function(element, value) {
        this._popupURL.update({qfilter: value});
    },

    popupURL: function(element) {
        return this._popupURL.render() || '';
    },

    reset: function(element) {
        this.val(element, null);
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.widget.input(element).val();
        }

        creme.widget.input(element).val(value);
        this._reloadLabel(element);
        element.trigger('change');
    },

    cleanedval: function(element) {
        var value = this.val(element);
        return Object.isEmpty(value) ? null : value;
    }
});

}(jQuery));
