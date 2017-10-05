/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2017  Hybird

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
 * Requires : jQuery, Creme
 */

(function($) {
"use strict";

creme.cti = {};

creme.cti.phoneCall = function(external_url, creme_url, number, entity_id) {
    creme.ajax.get({
                    url:   external_url,
                    data:  {n_tel: number},
                    error: function() {}
                   });
    creme.ajax.post({ //TODO: creme.ajax.json.post ???
                        url:      creme_url,
                        data:     {entity_id: entity_id},
                        dataType: 'json',
                        error:    function() { //TODO: better error message (wait for jsonify improvement)
                                      creme.dialogs.warning(gettext("Failed to create the phone call entity !")).open();
                                  },
                        success:  function(returnedData, status) {
                                      creme.dialogs.html($('<p>').append(returnedData), {'title': gettext("Phone call")}).open();
                                  }
                    });
};

}(jQuery));
