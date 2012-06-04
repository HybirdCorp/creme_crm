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
        field_value_name: '',
        parent_selector: 'td',
        object_id: ''
    },

    _create: function(element, options) {
        var self = creme.widget.AdaptiveWidget;

        element.data('url', options['url']);
        element.data('field_value_name', options['field_value_name']);
        element.data('parent_selector', options['parent_selector']);
        element.data('object_id', options['object_id']);

        element.bind('change', function() {
            self._change(element);
        });

        self._change(element);

        //self.val(element, self.val(element));
        element.addClass('widget-ready');
    },

    _change: function(element) {
        var $select = element.find('select');
        var $form = $select.parents('form');
        var value = $select.val();
        var field_value_name = element.data('field_value_name');
        var object_id = element.data('object_id');

        var $target = $form.find('[name='+field_value_name+']');
        var $parent_target = $target.parents(element.data('parent_selector'));

        creme.ajax.post({
            url: element.data('url'),
            dataType: 'json',
            data:{
                'field_name': value,
                'field_value_name': field_value_name,
                'object_id': object_id
            },
            success: function(data){
                $parent_target.empty().html(data.rendered);
                //$target.remove();
                //$parent_target.append($(data.rendered));
            }

        });

    }

});