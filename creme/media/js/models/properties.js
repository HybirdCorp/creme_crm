/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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

creme.properties = {};

creme.properties.select_one = function(creme_entity_id)
{
    this.show = function($node, text, titre)
    {
        $node.html(text);
        $node.dialog({
            buttons: { "Ok": function() {  
                                var $form = $(this).find('form:first');
                                if($form.size()>0)
                                    $form.submit();
                                $(this).dialog("destroy");
                                $(this).remove(); }
                     },
            closeOnEscape: false,
            hide: 'slide',
            show: 'slide',
            title: titre,
            modal: true
        });
    }

    var me = this;

    var current_url = window.location.href;
    

    $.ajax({
        type: "GET",
        url: '/creme_core/property/list_for_entity_ct/' + creme_entity_id,
        dataType: "text",
        async:false,
        data:{'callback_url' : current_url},
        success: function(data, status)
        {
            var $node = $('<div></div>');
            $('body').append($node);
            me.show($node, data, 'Séléctionnez une propriété');
        },
        error: function(request, status, error){
            var $node = $('<div></div>');
            $('body').append($node);
            me.show($node, '<b>Veuillez recharcher la page.</b>', 'Erreur');
        }
    });

}