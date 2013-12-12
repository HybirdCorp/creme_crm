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

creme.dialogs = creme.dialogs || {};

creme.dialogs = $.extend(creme.dialogs, {
    deprecatedForm: function(url, options, data)
    {
        var options = options || {};
        var dialog = new creme.dialog.FormDialog()
                                     .validator(function(data, statusText, dataType) {
                                                    return dataType !== 'text/html' || 
                                                           data.startsWith('<div class="in-popup" closing="true">');
                                                })
                                     .reload(url, data);;

        if (options.reloadOnSuccess) {
            dialog.onSuccess(function() {creme.utils.reload();});
        }

        return dialog;
    },

    deprecatedInnerPopupAction: function(url, options, data)
    {
        var options = $.extend({
                          submit_label: gettext("Save"),
                          submit: function(dialog) {
                              creme.utils.handleDialogSubmit(dialog);
                          },
                          validator: function() {
                              return true;
                          },
                          reloadOnSuccess: false
                      }, options || {});

        return new creme.component.Action(function() {
            var self = this;

            creme.utils.showInnerPopup(url,
                                       {
                                           send_button_label: options.submit_label,
                                           send_button: function(dialog) {
                                               try {
                                                   var submitdata = options.submit.apply(this, arguments);

                                                   if (options.validator(submitdata))
                                                   {
                                                       self.done(submitdata);
                                                       creme.utils.closeDialog(dialog, options.reloadOnSuccess);
                                                   }
                                               } catch(e) {
                                                   self.fail(e);
                                               }
                                           },
                                           close: function(event, ui) {
                                               creme.utils.closeDialog($(this), false);
                                               self.cancel();
                                           }
                                       },
                                       null,
                                       {
                                           error: function(req, status, error) {
                                               try {
                                                   creme.dialogs.warning(gettext("Error during loading the page.")).open();
                                                   self.fail(req, status, error);
                                               } catch(e) {
                                                   self.fail(req, status, error);
                                               }
                                           },
                                           data: data
                                       });
        });
    },

    deprecatedListViewAction: function(url, options, data)
    {
        var options = options || {};

        var selector = function(dialog) {
            return $('form[name="list_view_form"]').list_view("getSelectedEntitiesAsArray") || [];
        };

        var validator = function(data) {
              if (!Array.isArray(data) || data.length == 0) {
                  creme.dialogs.warning(gettext('Please select at least one entity.'), {'title': gettext("Error")}).open();
                  return false;
              }

              if (!options.multiple && data.length > 1) {
                  creme.dialogs.warning(gettext('Please select only one entity.'), {'title': gettext("Error")}).open();
                  return false;
              }

              return true;
        };

        return this.deprecatedInnerPopupAction(url, {
                   submit_label: gettext("Validate the selection"),
                   submit: function(dialog) {
                       var data = selector(dialog);
                       return validator(data) ? data : null;
                   },
                   validator: function(data) {
                       return data !== null;
                   }
               }, data);
    }
});
