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

(function($) {
    "use strict";

// if(!creme.relations) creme.relations = {}  ???
creme.lv_widget = {};

// TODO: beware it won't work from a Popover element with would be displayed in a popup list-view
//       (because popovers are detached from their original root in the DOM)
//       It should be fixed with the new action system like the bricks' one.
creme.lv_widget.findList = function(element) {
//    return $(element).parents('form.ui-creme-listview:first');
    var container = $(element).parents('.ui-dialog:first');

    if (container.length === 0) {
        container = $('body');
    }

    return container.find('form.ui-creme-listview:first');
};

creme.lv_widget.deleteEntityFilter = function(list, filterid) {
    console.warn('creme.lv_widget.deleteEntityFilter() is deprecated ; use creme.lv_widget.deleteFilter() instead.');

    var query = creme.utils.confirmPOSTQuery('/creme_core/entity_filter/delete', {}, {id: filterid});
    query.onDone(function(event, data) {
        list.list_view('reload');
    });

    return query.start();
};

creme.lv_widget.deleteHeaderFilter = function(list, filterid) {
    console.warn('creme.lv_widget.deleteHeaderFilter() is deprecated ; use creme.lv_widget.deleteFilter() instead.');

    var query = creme.utils.confirmPOSTQuery('/creme_core/header_filter/delete', {}, {id: filterid});
    query.onDone(function(event, data) {
        list.list_view('reload');
    });

    return query.start();
};

creme.lv_widget.deleteFilter = function(list, filter_id, url) {
    return creme.utils.confirmPOSTQuery(url, {}, {id: filter_id})
                      .onDone(function(event, data) {
                          list.list_view('reload');
                       })
                      .start();
};

creme.lv_widget.selectedLines = function(list) {
    list = $(list);

    if (list.list_view('countEntities') === 0) {
        return [];
    }

    return list.list_view('getSelectedEntitiesAsArray');
};

creme.lv_widget.DeleteSelectedAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _onDeleteFail: function(event, error, data) {
        var self = this;
        var list = this._list;

        var message = Object.isType(error, 'string') ? error : (error.message || gettext("Error"));
        var header = creme.ajax.localizedErrorMessage(data);
        var parser = new creme.utils.JSON();

        if (!Object.isEmpty(message) && parser.isJSON(message)) {
            var results = parser.decode(message);
            var removed_count = results.count - results.errors.length;

            header = '';

            if (removed_count > 0) {
                header = ngettext('%d entity have been deleted.',
                                  '%d entities have been deleted.',
                                  removed_count).format(removed_count);
            }

            if (results.errors) {
                header += ngettext(' %d entity cannot be deleted.',
                                   ' %d entities cannot be deleted.',
                                   results.errors.length).format(results.errors.length);
            }

            message = '<ul>' + results.errors.map(function(item) {
                                                 return '<li>' + item + '</li>';
                                              }).join('') +
                      '</ul>';
        }

        creme.dialogs.warning(message, {header: header})
                     .onClose(function() {
                          list.reload();
                          self.fail();
                      })
                     .open();
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var selection = creme.lv_widget.selectedLines(list);

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var query = creme.utils.confirmPOSTQuery(options.url, {warnOnFail: false, dataType: 'json'}, {ids: selection.join(',')});
            query.onFail(this._onDeleteFail.bind(this))
                 .onCancel(function(event, data) {
                     self.cancel();
                  })
                 .onDone(function(event, data) {
                     list.reload();
                     self.done();
                  })
                 .start();
        }
    }
});

creme.lv_widget.AddToSelectedAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var selection = creme.lv_widget.selectedLines(list);

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var dialog = creme.dialogs.form(options.url, {}, {ids: selection, persist: 'ids'});

            dialog.onFormSuccess(function(event, data) {
                       list.reload();
                       self.done();
                   })
                   .onClose(function() {
                       self.cancel();
                   })
                   .open({width: 800});
        }
    }
});

creme.lv_widget.EditSelectedAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var selection = creme.lv_widget.selectedLines(list);

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var dialog = creme.dialogs.form(options.url, {submitData: {entities: selection}});

            dialog.onFormSuccess(function(event, data) {
                       list.reload();
                       self.done();
                   })
                   .onFormError(function(event, data) {
                       if ($('form', this.content()).length === 0) {
                           this._updateButtonState('send', false);
                           this._updateButtonLabel('cancel', gettext('Close'));
                           this._bulk_edit_done = true;
                       }
                   })
                   .onClose(function() {
                       if (this._bulk_edit_done) {
                           list.reload();
                           self.done();
                       } else {
                           self.cancel();
                       }
                   })
                   .on('frame-update', function(event, frame) {
                       var summary = $('.bulk-selection-summary', frame.delegate());

                       if (summary.length) {
                           var count = selection.length;
                           var message = summary.attr('data-msg') || '';
                           var plural = summary.attr('data-msg-plural');

                           if (pluralidx(count)) {
                               message = plural || message;
                           }

                           // TODO: need all model select_label in djangojs.po files
                           // var content = ngettext(summary.attr('data-msg'), summary.attr('data-msg-plural'), count);
                           summary.text(message.format(selection.length));
                       }
                   })
                   .open({width: 800});
        }
    }
});

creme.lv_widget.MergeSelectedAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var selection = creme.lv_widget.selectedLines(list);

        if (selection.length !== 2) {
            creme.dialogs.warning(gettext("Please select 2 entities."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            try {
                creme.utils.goTo(options.url + '?' + $.param({id1: selection[0], id2: selection[1]}));
            } catch (e) {
                this.fail(e);
            }
        }
    }
});

creme.lv_widget.handleSort = function(sort_field, sort_order, new_sort_field, input, callback) {
    var $sort_field = $(sort_field);
    var $sort_order = $(sort_order);

    if ($sort_field.val() === new_sort_field) {
        if ($sort_order.val() === '') {
            $sort_order.val('-');
        } else {
            $sort_order.val('');
        }
    } else {
        $sort_order.val('');
    }

    $sort_field.val(new_sort_field);

    if (Object.isFunc(callback)) {
        callback(input);
    }
};

/*  creme.lv_widget.initialize = function(options, dialog) { */
creme.lv_widget.initialize = function(options, listview) {
    var submit_handler, history_handler;
    var dialog = listview.parents('.ui-dialog-content:first');
    var submit_url = options.reloadurl || window.location.pathname;
    var id = dialog.length > 0 ? dialog.attr('id') : undefined;

    if (id) {
        submit_handler = function(input, extra_data) {
            extra_data = id ? $.extend({whoami: id}, extra_data) : extra_data;
            var submit_options = {
                    action: submit_url,
                    success: function(event, data, status) {
                        data = id ? data + '<input type="hidden" name="whoami" value="' + id + '"/>' : data;
                        creme.widget.destroy(listview);
                        listview.html(data);
                        creme.widget.create(listview);
                    }
                };

            listview.list_view('setReloadUrl', submit_url);
            listview.list_view('handleSubmit', submit_options, input, extra_data);
        };
    } else {
        history_handler = function(url) {
            creme.history.push(url);
        };
        submit_handler = function(input, extra_data) {
            var submit_options = {
                    action: submit_url,
                    success: function(event, data, status) {
                        creme.widget.destroy(listview);
                        listview.html(data);
                        creme.widget.create(listview);
                    }
                };

            listview.list_view('handleSubmit', submit_options, input, extra_data);
        };
    }

    listview.list_view({
        o2m:              options.multiple ? 0 : 1,
        historyHandler:   history_handler,
        submitHandler:    submit_handler,
        kd_submitHandler: function (e, input, extra_data) {
            e = (window.event) ? window.event : e;
            var key = (window.event) ? e.keyCode : e.which;

            if (key === 13) {
                listview.list_view('getSubmit')(input, extra_data);
            }

            return true;
        }
    });

    // TODO : WTF ??
    $('.magnify', listview).imageMagnifier();
};

creme.lv_widget.listViewAction = function(url, options, data) {
    options = options || {};

    var selector = function(dialog) {
        var values = $('.ui-creme-listview tr.selected input[name="entity_id"]', dialog).map(function(index, item) {
                         return $(item).val();
                     });

        return values.get() || [];
    };

    var validator = function(data) {
          if (Object.isEmpty(data)) {
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
               },
               closeOnEscape: options.closeOnEscape
           }, data);
};

creme.lv_widget.ListViewActionBuilders = creme.component.Component.sub({
    _init_: function(list) {
        this._list = list;
    },

    _defaultDialogOptions: function(url, title) {
        var width = $(window).innerWidth();

        return {
            resizable: true,
            draggable: true,
            width: width * 0.8,
            maxWidth: width,
            url: url,
            title: title,
            compatible: true
        };
    },

    _action_update: function(url, options, data, e) {
        var list = this._list;
        var action;
        options = $.extend({action: 'post'}, options || {});

        if (options.confirm) {
            action = creme.utils.confirmAjaxQuery(url, options, data);
        } else {
            action = creme.utils.ajaxQuery(url, options, data);
        }

        return action.onDone(function() {
            list.reload();
        });
    },

    _action_delete: function(url, options, data, e) {
        return this._action_update(url, $.extend({}, options, {
            confirm: gettext('Are you sure ?')
        }), data, e);
    },

    _action_form: function(url, options, data, e) {
        var list = this._list;

        options = $.extend(this._defaultDialogOptions(url), options || {});

        return new creme.dialog.FormDialogAction(options, {
            'form-success': function() {
                list.reload();
             }
        });
    },

    _action_edit_selection: function(url, options, data, e) {
        return new creme.lv_widget.EditSelectedAction(this._list, {url: url});
    },

    _action_delete_selection: function(url, options, data, e) {
        return new creme.lv_widget.DeleteSelectedAction(this._list, {url: url});
    },

    _action_addto_selection: function(url, options, data, e) {
        return new creme.lv_widget.AddToSelectedAction(this._list, {url: url});
    },

    _action_merge_selection: function(url, options, data, e) {
        return new creme.lv_widget.MergeSelectedAction(this._list, {url: url});
    }
});

creme.lv_widget.ListViewLauncher = creme.widget.declare('ui-creme-listview', {
    options: {
        multiple:     false,
        whoami:       '',
        'reload-url': ''
    },

    _destroy: function($element) {
        $element.removeClass('widget-ready');
    },

    _create: function($element, options, cb, sync, args) {
        // var dialog = options.whoami ? $('#' + options.whoami) : undefined;
        var multiple = $element.is('[multiple]') || options.multiple;
        var $list = $element.find('.listview');

        // handle popup differentiation
        this._isStandalone = $list.hasClass('listview-standalone');
        $element.addClass(this._isStandalone ? 'ui-creme-listview-standalone'
                                             : 'ui-creme-listview-popup');

        if (this._isStandalone) {
            $list.find('.sticks-horizontally').css('transform', 'translateX(0)');
        }

        // Only init the $.fn.list_view once per form, not on every listview reload
        if (!$element.data('list_view')) {
            creme.lv_widget.initialize({
                multiple:  multiple,
                reloadurl: options['reload-url']
            }, $element);
        }

        // only hook up list behavior when there are rows
        var rowCount = $list.attr('data-total-count');
        if (rowCount <= 0) {
            return;
        }

        var $footer = $list.find('.list-footer-container');

        // pagination in popups
        if (!this._isStandalone) {
            var $popup = $element.parents('.ui-dialog').first();
            $footer.css('max-width', $popup.width());
        }

        // handle selection and hover border on floating header so that the first row is correctly styled
        $list.on('mouseenter', 'tr.selectable:first-child', function(e) {
            $list.addClass('first-row-hovered');
            if (this._isStandalone) {
                $('.listview.floatThead-table').addClass('first-row-hovered');
            }
        }.bind(this));

        $list.on('mouseleave', 'tr.selectable:first-child', function(e) {
            $list.removeClass('first-row-hovered');

            if (this._isStandalone) {
                $('.listview.floatThead-table').removeClass('first-row-hovered');
            }
        }.bind(this));

        $list.on('row-selection-changed', 'tbody tr:first-child', function(e, data) {
            $list.toggleClass('first-row-selected', data.selected);

            if (this._isStandalone) {
                $('.listview.floatThead-table').toggleClass('first-row-selected', data.selected);
            }
        }.bind(this));

        $element.addClass('widget-ready');

        // listview-popups have no floatThead, stickiness, vertical constraints etc
        if (!this._isStandalone) {
            return;
        }

        var headTop = $('.header-menu').height();

        $list.floatThead({
//            top: 35,
            top: headTop,
            zIndex: 97, // under the popups overlays, under the popovers and their glasspanes
            scrollContainer: function ($table) {
                return $table.closest('.sub_content');
            }
        });

        // when the page is loaded and the scrollbar is already scrolled past the header, notify it is already floated
        if ($(document).scrollTop() > $list.offset().top) {
            $('.floatThead-container').addClass('floated');
            $list.addClass('floated');
        }

        // or when the floatThead script floats it automatically
        $list.on('floatThead', function(e, isFloated, $floatContainer) {
            if (isFloated) {
                $floatContainer.addClass('floated');
                $(this).addClass('floated');

                // vertical constraint 2 : close header actions popovers when they would collide with the floating header scrolling
                $('.header-actions-popover').trigger('modal-close');
            } else {
                $floatContainer.removeClass('floated');
                $(this).removeClass('floated');
            }
        });

        // the anchor will hold the header shadow
//        $('<div class="floated-header-anchor">').css({
//            'position': 'fixed',
//            'top': 35 /* menu height */ + $('.floatThead-container').innerHeight() - 4 /* padding + borders */ - 10 /* shadow height */
//        }).insertAfter('.floatThead-container');
        var anchor = $('<div class="floated-header-anchor">');
        anchor.insertAfter('.floatThead-container');

        var headerHeight = $($('.floatThead-container').children().get(0)).height(); // we use the height of the contained table because it excludes its own padding
        var anchorHeight = anchor.height();

        anchor.css({
            'position': 'fixed',
            // NB it would be great if we could get the bottom of '.floatThead-container' & set the same bottom to the anchor...
            'top': headTop + headerHeight - anchorHeight
        });

        this._pager = new creme.list.Pager();
        this._pager.on('refresh', function(event, page) {
                        $element.data('list_view').getSubmit()(null, {page: page});
                    })
                   .bind($list.find('.listview-pagination'));
    }
});


}(jQuery));
