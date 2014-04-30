/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2014  Hybird

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

creme.widget.DatePicker = creme.widget.declare('ui-creme-datepicker', {
    options: {
        format:'dd-mm-yy'
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;
        var parent = element.parent()
        var today = $('<button>').attr('name', 'today').html(gettext('Today'))
                                 .attr('type', 'button')
                                 .bind('click', function(e) {
                                                     element.datepicker('setDate', new Date());
                                                     element.change();
                                                     return false;
                                                });

        var list = $('<ul/>').addClass('ui-layout hbox').append($('<li/>').append(element));

        parent.append(list);

        element.datepicker({dateFormat: options.format,
                            showOn: "button",
                            buttonText: gettext('Calendar'),
                            buttonImage: creme_media_url('images/icon_calendar.gif'),
                            buttonImageOnly: true });

        list.append($('<li/>').append($('<span/>').addClass('ui-creme-datepicker-trigger')
                                                  .append($('img.ui-datepicker-trigger', parent))))
            .append($('<li/>').append(today));

        element.addClass('widget-ready');
    }
});
