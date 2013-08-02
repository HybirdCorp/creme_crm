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

creme.widget.ActionButtonList = creme.widget.declare('ui-creme-actionbuttonlist', {
    options: {
        debug: true
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;
        this._selector = creme.widget.create(self.selector(element));

        self.actions(element).click(function() {
            return self._handle_action(element, $(this));
        });

        $(element).bind('selectorlist-added', function(e, selector) {
            self._selector.element.triggerHandler('selectorlist-added', self._selector);
        });

        element.addClass('widget-ready');
    },

    actions: function(element) {
        return $('> li > button.ui-creme-actionbutton', element);
    },

    action: function(element, index) {
        return $('> li > button.ui-creme-actionbutton:nth(' + index + ')', element);
    },

    selector: function(element) {
        return $('> li.delegate > .ui-creme-widget', element);
    },

    dependencies: function(element) {
        return creme.object.delegate(this._selector, 'dependencies') || [];
    },

    reload: function(element, data, cb, error_cb, sync) {
        return creme.object.delegate(this._selector, 'reload', data, cb, error_cb, sync);
    },

    val: function(element, value) {
        return creme.object.delegate(this._selector, 'val', value) || '';
    },

    reset: function(element, value) {
        return creme.object.delegate(this._selector, 'reset');
    },

    cleanedval: function(element) {
        return creme.object.delegate(this._selector, 'cleanedval') || null;
    },

    update: function(element, data) {
        return creme.object.delegate(this._selector, 'update');
    },

    _on_action_success: function(element, data, statusText, dataType)
    {
        var self = this;
        var delegate = this._selector;
        var item = creme.widget.parseval(data, creme.ajax.json.parse);

        if (Object.isEmpty(delegate))
            return;

        if (item != null) {
            delegate.update(data);
        } else {
            delegate.reload();
        }
    },

    _handle_action: function(element, button)
    {
        var self = this;
        var action = creme.widget.parseopt(button, {action:'popup'}).action;

        var handler = self['_handle_action_' + action];

        if (handler !== undefined)
            self['_handle_action_' + action](element, button);

        return false;
    },

    _handle_action_reset: function(element, button)
    {
        var options = creme.widget.parseopt(button, {value: ''});
        this._on_action_success(element, {value:options.value}, 'success');
    },

    _handle_action_popup: function(element, button)
    {
        var self = this;
        var options = creme.widget.parseopt(button, {popupResizable: true,
                                                     popupDraggable: true,
                                                     popupWidth: window.screen.width / 2,
                                                     popupHeight: 356,
                                                     url: '',
                                                     title: ''});

        var action = new creme.component.FormDialogAction()

        action.onDone(function(event, data) {
                          element.trigger('actionSuccess', [data])
                          self._on_action_success(element, data);
                      })
              .onCancel(function(event) {
                            element.trigger('actionCanceled');
                        })
              .start(options);
    }
});
