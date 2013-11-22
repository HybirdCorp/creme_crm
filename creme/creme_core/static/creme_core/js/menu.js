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

/*
 * Requires : jQuery
 *            creme
 */

creme.menu = {};
creme.menu.actions = {};

creme.menu.actions.flatMenu = function(trigger_selector, content_selector) {
    $(trigger_selector).menu({
            content: $(content_selector).html(),
            showSpeed: 400
    });

    $('[role=menuitem]','[aria-labelledby="' + trigger_selector.replace('#', '') + '"]')
    .live('menu-item-selected', function(e, menu) {
        e.stopImmediatePropagation();

        var $a = $('a:first', this);

        //TODO: use 3 classes: 'confirm', 'post', 'ajax'
        if($a.hasClass('confirm')) {
            creme.utils.confirmBeforeGo($a.attr('href'), true, {type: "POST"});
        } else {
            creme.utils.goTo($a.attr('href'));
        }
    });
};

creme.menu.NavIt = function(trigger_selector, options) {
    $(trigger_selector).NavIt(options || {});

    $(trigger_selector).find('a').click(function(e) {
        var $a = $(this);
        var confirm   = $a.hasClass('confirm');
        var post      = $a.hasClass('post');
        var ajax      = $a.hasClass('ajax');
        var list_view = $a.hasClass('lv_reload');

        var opts = {
            type: (post)? "POST": "GET"
        }

        e.preventDefault();

        if (ajax && list_view) {
            opts = $.extend(opts, {
                success: function(data, status, req) {
                    //creme.utils.showDialog(gettext("Operation done"));
                    $a.parents('form').list_view('reload');
                },
                error: function(req, status, error) { //TODO: factorise
//                     if(!req.responseText || req.responseText == "") {
//                         creme.utils.showDialog(gettext("Error"));
//                     } else {
//                         creme.utils.showDialog(req.responseText);
//                     }
                    creme.dialogs.warning(req.responseText || gettext("Error"));
                }
            });
        }

        if (confirm) {
            creme.utils.confirmBeforeGo($a.attr('href'), ajax, opts);
        } else {
            creme.utils.goTo($a.attr('href'));
        }

    });
};

creme.menu.HNavIt = function(trigger_selector, options) {
    creme.menu.NavIt(trigger_selector, $.extend({ArrowSideOnRight: false}, options));
}