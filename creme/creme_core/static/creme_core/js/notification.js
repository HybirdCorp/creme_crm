/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2024  Hybird

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

/*
 * Requires : jQuery
 *            creme
 */

(function($) {
"use strict";

creme.notification = {};

/* TODO: unit tests */
/* globals setInterval creme_media_url */
creme.notification.NotificationBox = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            refreshDelay: 300000  // In milliseconds. Default 5 minutes.
        }, options || {});

        this._refreshDelay = options.refreshDelay;

        this._initialDataSelector = options.initialDataSelector;
        if (Object.isEmpty(this._initialDataSelector)) {
            throw new Error('initialDataSelector is required');
        }

        this._refreshUrl = options.refreshUrl;
        if (Object.isEmpty(this._refreshUrl)) {
            throw new Error('refreshUrl is required');
        }

        this._discardUrl = options.discardUrl;
        if (Object.isEmpty(this._discardUrl)) {
            throw new Error('discardUrl is required');
        }

        this._count = 0;
        this._overlay = new creme.dialog.Overlay();
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('NotificationBox is already bound');
        }

        this._element = element;

        this._updateBox(
            JSON.parse(creme.utils.JSON.readScriptText(element.find(this._initialDataSelector)))
        );

        // Activate panel on hover events
        element.on('mouseenter', function(e) {
            $(this).addClass('notification-box-activated');
        }).on('mouseleave', function(e) {
            $(this).removeClass('notification-box-activated');
        });

        // NB: we attach to <ul> & not the parent <div> because the overlay sets
        //     the position as "relative" (which breaks our layout).
        //     It's even better because by doing this way the overlay does not
        //     hide the link "See all notifications".
        this._overlay.bind($('.notification-items', element))
                     .addClass('notification-loading')
                     .content(
                        '<h2><img src="${src}"><span>${label}</span></h2>'.template({
                            src: creme_media_url('images/wait.gif'),
                            label: gettext('Loading…')
                        })
                     );

        // TODO: <() => this._refresh()> with more modern JS
        setInterval(this._refresh.bind(this), this._refreshDelay);

        return this;
    },

    _humanizedTimeDelta: function(secondsTimedelta) {
        var minutesTimeDelta = Math.round(secondsTimedelta / 60);

        if (minutesTimeDelta < 60) {
            return ngettext(
                '%d minute ago', '%d minutes ago', minutesTimeDelta
            ).format(minutesTimeDelta);
        }

        var hoursTimeDelta = Math.floor(minutesTimeDelta / 60);

        if (hoursTimeDelta < 24) {
            return ngettext(
                'More than %d hour ago', 'More than %d hours ago', hoursTimeDelta
            ).format(hoursTimeDelta);
        }

        var daysDelta = Math.floor(hoursTimeDelta / 24);
        return ngettext(
            'More than %d day ago', 'More than %d days ago', daysDelta
        ).format(daysDelta);
    },

    _updateCounter: function(count) {
        this._count = count;
        var countWidget = this._element.find('.notification-box-count');
        countWidget.text(count);
        countWidget.toggleClass('is-empty', !count);
    },

    _updateItems: function(notifications) {
        var element = this._element;
        var discardUrl = this._discardUrl;
        var itemsWidget = element.find('.notification-items');
        itemsWidget.empty();

        var now_ts = Date.now();
        var box = this;
        notifications.map(function(itemData) {
            var notif_id = itemData.id;
            var button = $(
                '<button type="button" class="discard-notification">${label}</button>'.template(
                    {label: gettext('Validate')}
                )
            ).on('click', function(e) {
                // e.preventDefault();
                creme.utils.ajaxQuery(
                    discardUrl,
                    {action: 'post', warnOnFail: true},
                    {id: notif_id}
                ).onDone(function() {
                    element.find('[data-notification-id="${id}"]'.template({id: notif_id})).remove();
                    box._updateCounter(box._count - 1);
                }).start();
            });

            var created_ts = Date.parse(itemData.created);
            var created = new Date(created_ts);
            var item = $(
                (
                    '<li class="notification-item notification-item-level${level}" data-notification-id="${id}">' +
                        '<span class="notification-channel">${channel}</span>' +
                        '<span class="notification-subject">${subject}</span>' +
                        '<span class="notification-created" title="${created}">${humanized_created}</span>' +
                        '<div class="notification-body">${body}</div>' +
                    '</li>'
                ).template({
                    id: notif_id,
                    level: itemData.level,
                    channel: itemData.channel,
                    created: created.toLocaleString(),
                    // TODO: update dynamically this label every minute
                    humanized_created: this._humanizedTimeDelta(Math.round((now_ts - created_ts) / 1000)),
                    subject: itemData.subject,
                    body: itemData.body
            })).append(button);

            itemsWidget.append(item);
        }.bind(this));
    },

    _updateBox: function(data) {
        this._updateCounter(data.count);
        this._updateItems(data.notifications);
    },

    _updateErrorMessage: function(message) {
        var container = this._element.find('.notification-error');
        container.toggleClass('is-empty', message === undefined || message === '');
        container.find('span').text(message || '');
    },

    _refresh: function() {
        /* TODO: our script will continue to be called even if the tab is not visible
           (at least on PS -- it seems iOS does not wake up not visible tabs).
           Here we do not query the server when the tab is not visible, so we avoid
           to flood the server when there are many Creme tabs.
           Should we remove the interval when the tab is hidden (and code a way to
           query the server every time 'refreshDelay' milliseconds have been spend
           in visible mode)?
           Hint: see <document.addEventListener("visibilitychange", function() {....})>
        */
        if (document.hidden) {
            return;
        }

        var overlay = this._overlay;
        overlay.visible(true);

        creme.ajax.query(
            this._refreshUrl, {backend: {sync: false, dataType: 'json'}}
        ).onDone(
            function(event, data) {
                this._updateBox(data);
                this._updateErrorMessage();
            }.bind(this)
        ).onFail(
            function(event, data, error) {
                /* E.g.
                 - event === fail
                 - data === undefined
                 - error === {type: 'request', status: 0, request: {…}, message: 'HTTP 0 - error'}
                */
                this._updateErrorMessage(
                    gettext('An error happened when retrieving notifications (%s)').format(error.message)
                );
            }.bind(this)
        ).onComplete(
            function() { overlay.visible(false); }
        ).start();
    }
});

}(jQuery));
