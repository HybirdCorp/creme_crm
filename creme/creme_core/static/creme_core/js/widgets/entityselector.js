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

creme.widget.EntitySelector = creme.widget.declare('ui-creme-entityselector', {
	options : {
		url:'',
		multiple:0,
		source:function(url, cb, error_cb, sync) {
			creme.ajax.json.get(url, {fields:['unicode']}, cb, error_cb, sync);
		}
	},

	_create: function(element, options) {
		var self = creme.widget.EntitySelector;

		element.data('popup', options['url']);
		
		$(element).bind('click', function() {
			self._select(element, $(this));
		});
		
		self.val(element, self.val(element));
		element.addClass('widget-ready');
	},
	
	reload: function(element, url, cb, error_cb, sync) {
		var self = creme.widget.EntitySelector;
		self.val(element, null);
		element.data('popup', url);
	},
	
	_update: function(element, values) {
		var self = creme.widget.EntitySelector;
		self.val(element, values[0]);
	},
	
	_select: function(element, content_type, cb) {
		console.log(element.data('popup'), element);
		
		var self = creme.widget.EntitySelector
		var o2m = (creme.widget.options($(element))['multiple'] === '1') ? '0' : '1'
		var url = $(element).data('popup') + '/' + o2m;
		
		creme.utils.showInnerPopup(url, {
				'send_button_label': 'Valider la selection',
				'send_button': function(dialog)
					{
						var lv = $('form[name="list_view_form"]');
				        var result = lv.list_view("getSelectedEntitiesAsArray");
				        
				        if (result.length == 0) {
				        	creme.utils.showDialog("Veuillez sélectioner au moins un enregistrement !", {'title':'Erreur'});
				        	return;
				        }
				        
				        self._update(element, result);
				        creme.utils.closeDialog(dialog, false);
					}
			});
	},
	
	val: function(element, value) {
		if (value !== undefined) {
			var input = creme.widget.input(element);
			var button = $('button', element);
			
			if (value !== null && value !== '') {
				var url = creme.widget.template(button.attr('url'), {'id':value});
				creme.ajax.json.get(url, {fields:['unicode']}, 
						function(data) {
							button.text(data[0][0]);
							input.val(value);
							element.trigger('change');
						},
						function(error) {
							button.text(button.attr('label'));
						},
						true);
			} else {
				button.text(button.attr('label'));
				input.val(value);
				element.trigger('change');
			}
		} else {
			res = creme.widget.input(element).val();
			return (res) ? res : null;
		}
	},
	
	clone: function(element) {
		var self = creme.widget.EntitySelector;
		var copy = creme.widget.clone(element);
		copy.val(element.val(value));
		return copy;
	}
});
