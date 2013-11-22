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

creme.dialog = creme.dialog || {};

creme.dialog.ConfirmDialog = creme.dialog.Dialog.sub({
    _init_: function(message, options) {
        var options = $.extend({
            title:    gettext('Confirm'),
            fitFrame: false,
            height:   200
        }, options || {});

        this._super_(creme.dialog.Dialog, '_init_', options);
        this.message(message);
    },

    ok: function()
    {
        this._destroyDialog();
        this._events.trigger('ok', [], this);
        return this;
    },

    message: function(message)
    {
        this.options.html = '<p>' + message + '</p>';
        return this.isOpened() ? this.fill(this.options.html) : this;
    },

    _populateButtons: function(buttons, options)
    {
        this._appendButton(buttons, 'ok', gettext('Ok'), this.ok);
        this._appendButton(buttons, 'cancel', gettext('Cancel'), this.close);

        return buttons;
    },

    onOk: function(cb) {
        this._events.bind('ok', cb);
        return this;
    }
});


creme.dialog.ConfirmAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._openPopup, options);
    },

    _openPopup: function(options)
    {
        var self = this;

        new creme.dialog.ConfirmAction(options).onSuccess(function(data) {self.done();})
                                               .onClose(function() {self.cancel();})
                                               .open();
    }
});
