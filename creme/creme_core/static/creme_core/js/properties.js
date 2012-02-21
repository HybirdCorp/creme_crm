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

// Commented on 21 february 2012
// creme.properties = {};
// 
// creme.properties.get_types = function(ct_id) {
//     var types = [];
//     var success_cb = function(data, status) {
//         for(var i in data) {
//             var d = data[i];
//             types.push({pk: d.pk, text: d.fields['text']})
//         }
//     }
//     creme.ajax.json.post('/creme_core/property/get_types', {'ct_id': ct_id}, success_cb, null, true);
//     return types;
// }