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

creme.widget.AdaptiveWidget = creme.widget.declare('ui-creme-adaptive-widget', {
    options : {
        url: '',
        object_id: ''
    },

    _create: function(element, options, cb)
    {
        var self = this;

        element.bind('change', function() {
            self._updateFieldWidget(element);
        });

        this._updateFieldWidget(element, {
            done: function() {
                element.addClass('widget-ready');
                creme.object.invoke(cb, element);
            } 
        });
    },

    _updateFieldWidget: function(element, listeners)
    {
        var options = this.options;
        var listeners = listeners || {};

        var $select = element.find('select');
        var $form = $select.parents('form');
        var field_name = $select.val();

        var $target = $form.find('[name="field_value"]');
        var $parent_target = $target.parents('td:first');

        var query = creme.ajax.query(options.url, {backend: {dataType: 'json'}})
                              .onDone(function(event, data) {
                                   $parent_target.empty().html(data.rendered);
                                   creme.widget.ready($parent_target);
                               })
                              .on(listeners);

        query.get({
                  'field_name': field_name,
                  'object_id': options.object_id
              });
    }

});