/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2015  Hybird

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

// if(!creme.relations) creme.relations = {}  ???
creme.lv_widget = {};

creme.lv_widget.openFilterSelection = function(ct_id, q_filter, multiple, listeners) {
    creme.lv_widget.listViewAction('/creme_core/list_view/popup/%s/%s?q_filter=%s'.format(ct_id, multiple ? 0 : 1, q_filter), {multiple:multiple})
                   .one(listeners)
                   .start();
}

creme.lv_widget.openFilterView = function(ct_id, q_filter) {
    creme.utils.showInnerPopup('/creme_core/list_view/popup/%s/%s?q_filter=%s'.format(ct_id, 1, q_filter), {
                                   closeOnEscape: true,
                                   open: function() {},
                                   buttons: [{text: gettext("Ok"),
                                              click: function() {
                                                         $(this).dialog("close");
                                                     }
                                             }],
                               });
}

creme.lv_widget.deleteEntityFilter = function(list, filterid) {
    var query = creme.utils.confirmPOSTQuery('/creme_core/entity_filter/delete', {}, {id: filterid});
    query.onDone(function(event, data) {list.list_view('reload');});
    return query.start();
}

creme.lv_widget.deleteHeaderFilter = function(list, filterid) {
    var query = creme.utils.confirmPOSTQuery('/creme_core/header_filter/delete', {}, {id: filterid});
    query.onDone(function(event, data) {list.list_view('reload');});
    return query.start();
}

creme.lv_widget.selectedLines = function(list) {
    var list = $(list);

    if (list.list_view('countEntities') == 0)
        return [];

    return list.list_view('getSelectedEntitiesAsArray');
}

creme.lv_widget.deleteSelectedLines = function(list) {
    var list = $(list);
    var selection = creme.lv_widget.selectedLines(list);
    var parser = new creme.utils.JSON();

    if (!selection.length) {
        creme.dialogs.warning(gettext("Please select at least one entity.")).open();
        return;
    }

    var query = creme.utils.confirmPOSTQuery('/creme_core/entity/delete/multi', {warnOnFail: false, dataType:'json'}, {ids: selection.join(',')});
    query.onFail(function(event, error, data) {
              var message = Object.isType(error, 'string') ? error : (error.message || gettext("Error"));
              var header = creme.ajax.localizedErrorMessage(data);

              if (!Object.isEmpty(message) && parser.isJSON(message))
              {
                  var results = parser.decode(message);
                  var removed_count = results.count - results.errors.length;

                  header = '';

                  if (removed_count > 0) {
                      header = ngettext('%d entity have been deleted.',
                                        '%d entities have been deleted.',
                                        removed_count).format(removed_count)
                  }

                  if (results.errors) {
                      header += ngettext(' %d entity cannot be deleted.',
                                         ' %d entities cannot be deleted.',
                                         results.errors.length).format(results.errors.length);
                  }

                  message = '<ul>' + results.errors.map(function(item) {return '<li>' + item + '</li>'}).join('') + '<ul>';
              }

              creme.dialogs.warning(message, {header: header})
                           .onClose(function() {list.list_view('reload');})
                           .open();
          })
         .onDone(function(event, data) {list.list_view('reload');});

    return query.start();
}

creme.lv_widget.addToSelectedLines = function(list, url) {
    var list = $(list);
    var selection = creme.lv_widget.selectedLines(list);

    if (!selection.length) {
        creme.dialogs.warning(gettext("Please select at least one entity.")).open();
        return;
    }

    var action = creme.utils.innerPopupFormAction(url, {}, {ids: selection, persist: 'ids'});

    action.onDone(function(event, data) {
              list.list_view('reload');
           })
          .start();

    return action;
}

creme.lv_widget.editSelectedLines = function(list, url) {
    var list = $(list);
    var selection = creme.lv_widget.selectedLines(list);

    if (!selection.length) {
        creme.dialogs.warning(gettext("Please select at least one entity.")).open();
        return;
    }

    var dialog = creme.dialogs.form(url, {
                                       submitData: {entities: selection}
                                    });

    dialog.onFormSuccess(function(event, data) {
              list.list_view('reload');
           })
          .onFormError(function(event, data) {
              if ($('form', this.content()).length == 0) {
                  this._updateButtonState('send', false);
                  this._updateButtonLabel('cancel', gettext('Close'));
                  this._bulk_edit_done = true;
              }
           })
          .onClose(function() {
              if (this._bulk_edit_done) {
                  list.list_view('reload');
              }
           })
          .on('frame-update', function(event, frame) {
              var summary = $('.bulk-selection-summary', frame.delegate());

              if (summary.length) {
                  var count = selection.length;
                  var content = ngettext(summary.attr('data-msg'), summary.attr('data-msg-plural'), count);
                  summary.text(content.format(selection.length));
              }
          })
          .open({width:800});

    return dialog;
}

creme.lv_widget.handleSort = function(sort_field, sort_order, new_sort_field, input, callback) {
    var $sort_field = $(sort_field);
    var $sort_order = $(sort_order);

    if($sort_field.val() == new_sort_field) {
        if($sort_order.val() == "") {
            $sort_order.val("-");
        } else {
            $sort_order.val("");
        }
    } else {
        $sort_order.val("");
    }
    $sort_field.val(new_sort_field);
//     if(typeof(callback) == "function") callback(input);
    if ($.isFunction(callback))
        callback(input);
}

creme.lv_widget.initialize = function(options, dialog) {
    var id = dialog ? dialog.attr('id') : undefined;
    var listview = $('form[name="list_view_form"]', dialog);
    var submit_url = (dialog ? $('[name="inner_header_from_url"]', dialog).val() : '') + '?ajax=true';
    var submit_handler;

    if (id) {
        submit_handler = function(input, extra_data) {
            var extra_data = id ? $.extend({whoami: id}, extra_data) : extra_data;
            var submit_options = {
                    action: submit_url,
                    success: function(data, status) {
                        var data = id ? data + '<input type="hidden" name="whoami" value="' + id + '"/>' : data;
                        $(input.form).html(data);
                    }
                };

            $(input.form).list_view('setReloadUrl', submit_url);
            $(input.form).list_view('handleSubmit', input.form, submit_options, input, extra_data);
        }
    } else {
        submit_handler = function(input, extra_data) {
            var submit_options = {
                    action: submit_url,
                    success: function(data, status) {$(input.form).html(data);}
                };

            $(input.form).list_view('handleSubmit', input.form, submit_options, input, extra_data);
        }
    }

    listview.list_view({
        o2m:              options.multiple ? 0 : 1,
        submitHandler:    submit_handler,
        kd_submitHandler: function (e, input, extra_data)
        {
            var e = (window.event) ? window.event : e;
            var key= (window.event) ? e.keyCode : e.which;

            if (key === 13) {
                $(input.form).list_view('getSubmit')(input, extra_data);
            }

            return true;
        }
    });

    // TODO : WTF ??
    $('.magnify', dialog).imageMagnifier();
};


creme.lv_widget.listViewAction = function(url, options, data) {
    var options = options || {};

    var selector = function(dialog) {
        var values = $('form[name="list_view_form"] tr.selected input[name="entity_id"]', dialog).map(function(index, item) {
                         return $(item).val();
                     });

        return values.get() || [];
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

    return creme.utils.innerPopupFormAction(url, {
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

creme.lv_widget.ListViewLauncher = creme.widget.declare('ui-creme-listview', {
    options: {
        multiple: false,
        whoami:   '',
    },

    _create: function(element, options, cb, sync, arguments)
    {
        var dialog = options.whoami ? $('#' + options.whoami) : undefined;
        var multiple = element.is('[multiple]') || options.multiple

        creme.lv_widget.initialize({multiple: multiple}, dialog);

        /* TODO : remove it, "default-action" class is no longer used in templates.
        $('.list_view_actions .default-action', element).hover(
             function() {$(this).addClass('ui-state-hover');},
             function() {$(this).removeClass('ui-state-hover');}
        );
        */

        element.addClass('widget-ready');
    }
});
