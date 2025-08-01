/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

creme.lv_widget = {};

creme.lv_widget.ListViewSelectionMode = {
    NONE: 'none',
    MULTIPLE: 'multiple',
    SINGLE: 'single'
};

creme.lv_widget.checkSelectionMode = function(mode) {
    if (Object.values(creme.lv_widget.ListViewSelectionMode).indexOf(mode) === -1) {
        throw Error('invalid listview selection mode ' + mode);
    } else {
        return mode;
    }
};

creme.lv_widget.ExportAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var formats = options.formats || [['', 'No backend found']];

        creme.dialogs.choice(gettext("Select the export format"), {
            title: gettext("Export"),
            choices: formats.map(function(item) {
                return {value: item[0], label: item[1]};
            }),
            required: true
        }).onOk(function(event, data) {
           creme.utils.goTo(options.url, {type: data});
           self.done();
        }).onClose(function() {
            self.cancel();
        }).open();
    }
});

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

        if (!Object.isEmpty(message) && _.isJSON(message)) {
            var results = JSON.parse(message);
            var removed_count = results.count - results.errors.length;

            header = '';

            if (removed_count > 0) {
                header = ngettext('%d entity has been deleted.',
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
        var selection = list.selectedRows();

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var query = creme.utils.ajaxQuery(options.url, {
                action: 'POST',
                confirm: true,
                warnOnFail: false,
                dataType: 'json'
            }, {ids: selection.join(',')});

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
        var selection = list.selectedRows();

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var dialog = creme.dialogs.form(options.url, {
                                                submitData: {ids: selection}
                                            }, {
                                                ids: selection
                                            });

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
        this._isEditionDone = false;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var isEditionDone = false;
        var selection = list.selectedRows();

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one entity."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var dialog = new creme.dialog.FormDialog({
                url: options.url,
                data: {
                    entities: selection.join('.')
                },
                submitData: {entities: selection},
                // DO NOT close the popup on form success !
                closeOnFormSuccess: false
            });

            dialog.onFormSuccess(function(event, data) {
                       // The summary must be shown, so we cannot close the
                       // dialog now. Just store the successful state
                       isEditionDone = true;
                   })
                   .onClose(function() {
                       if (isEditionDone) {
                           list.reload();
                           self.done();
                       } else {
                           self.cancel();
                       }
                   })
                   .on('frame-update', function(event, frame) {
                       frame.delegate().on('change', '[name="_bulk_fieldname"]', function() {
                           var next = $(this).val();
                           if (!Object.isNone(next) && next !== dialog.frame().lastFetchUrl()) {
                               dialog.fetch(next);
                           }
                       });
                   });

             dialog.open({width: 800});
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
        var selection = list.selectedRows();

        if (selection.length !== 2) {
            creme.dialogs.warning(gettext("Please select 2 entities."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            try {
                creme.utils.goTo(options.url, {id1: selection[0], id2: selection[1]});
            } catch (e) {
                this.fail(e);
            }
        }
    }
});

creme.lv_widget.ListViewDialog = creme.dialog.Dialog.sub({
    _init_: function(options) {
        options = $.extend({
            title: '',
            useListTitle: true,
            selectionMode: 'single',
            selectionValidator: this._defaultValidator,
            width: '80%'
        }, options || {});

        this._super_(creme.dialog.Dialog, '_init_', options);
        this.selectionValidator(options.selectionValidator);
        this.selectionMode(options.selectionMode);

        this._bindListView();
    },

    _bindListView: function() {
        var self = this;

        this.on('frame-update', function() {
            self.content().on('listview-bind-complete', '.ui-creme-listview', function() {
                self._updateDialogTitle();
            });
        });
    },

    _onFrameFail: function(event, data, error) {
        var buttons = {};

        this._appendButton(buttons, 'close', gettext('Close'), function(button, e, options) {
            this.close();
        });

        this.replaceButtons(buttons);

        this._super_(creme.dialog.Dialog, '_onFrameFail', event, data, error);
    },

    _updateDialogTitle: function() {
        var container = this.content().find('.list-title');

        container.toggleClass('hidden', this.options.useListTitle);

        if (this.options.useListTitle) {
            var title = this.options.title;
            var subtitle = container.find('.list-sub-title').text();
            var stats = container.find('.list-title-stats').text();

            if (Object.isEmpty(title)) {
                title = container.find('.list-main-title').text();
            }

            this.title("${title}${subtitle} ${stats}".template({
                title: title,
                subtitle: Object.isEmpty(subtitle) ? '' : [' − ', subtitle].join(''),
                stats: stats
            }));
        }
    },

    selectionMode: function(mode) {
        if (mode === undefined) {
            return this._selectionMode;
        }

        this._selectionMode = creme.lv_widget.checkSelectionMode(mode);

        var controller = this.controller();

        if (Object.isNone(controller) === false) {
            controller.submitState({selection: mode});
        }

        return this;
    },

    isSelectable: function() {
        return this.selectionMode() !== creme.lv_widget.ListViewSelectionMode.NONE;
    },

    isMultiple: function() {
        return this.selectionMode() === creme.lv_widget.ListViewSelectionMode.MULTIPLE;
    },

    isSingle: function() {
        return this.selectionMode() === creme.lv_widget.ListViewSelectionMode.SINGLE;
    },

    _frameFetchData: function(options, data) {
        var fetchData = this._super_(creme.dialog.Dialog, '_frameFetchData', options, data);
        return $.extend({}, fetchData, {
            selection: this.selectionMode()
        });
    },

    _defaultValidator: function(rows) {
        if (!this.isSelectable()) {
            return true;
        }

        if (Object.isEmpty(rows)) {
            creme.dialogs.warning(gettext('Please select at least one entity.'), {'title': gettext("Error")}).open();
            return false;
        }

        if (!this.isMultiple() && rows.length > 1) {
            creme.dialogs.warning(gettext('Please select only one entity.'), {'title': gettext("Error")}).open();
            return false;
        }

        return true;
    },

    selectionValidator: function(validator) {
        return Object.property(this, '_validator', validator);
    },

    controller: function() {
        return this.content().find('.ui-creme-listview').list_view('instance');
    },

    selected: function() {
        var controller = this.controller();
        return Object.isNone(controller) ? [] : controller.selectedRows();
    },

    validate: function() {
        var validator = this._validator;
        var selected = this.selected();

        if (Object.isFunc(validator) && validator.apply(this, [selected]) === false) {
            return this;
        }

        this._destroyDialog();
        this._events.trigger('validate', [selected], this);
        return this;
    },

    _defaultButtons: function(buttons, options) {
        if (this.isSelectable()) {
            this._appendButton(buttons, 'validate', gettext('Validate the selection'), function(button, e, options) {
                                   this.validate();
                               });
            this._appendButton(buttons, 'close', gettext('Cancel'), function(button, e, options) {
                                   this.close();
                               });
        } else {
            this._appendButton(buttons, 'close', gettext('Close'), function(button, e, options) {
                                   this.close();
                               });
        }

        return buttons;
    },

    onValidate: function(cb) {
        this._events.on('validate', cb);
        return this;
    }
});

creme.lv_widget.ListViewDialogAction = creme.component.Action.sub({
    _init_: function(options, listeners) {
        this._super_(creme.component.Action, '_init_', this._openPopup, options);
        this._listeners = listeners || {};
    },

    _onValidate: function(event, selected) {
        this.done(selected);
    },

    _buildPopup: function(options) {
        var self = this;
        options = $.extend(this.options(), options || {});

        var dialog = new creme.lv_widget.ListViewDialog(options).onValidate(this._onValidate.bind(this))
                                                                .onClose(function() {
                                                                    self.cancel();
                                                                 })
                                                                .on(this._listeners);

        return dialog;
    },

    _openPopup: function(options) {
        this._buildPopup(options).open();
    }
});

creme.lv_widget.ListViewActionLink = creme.action.ActionLink.sub({
    _init_: function(list, options) {
        this._super_(creme.action.ActionLink, '_init_', options);
        this._list = list;

        this.on('action-link-start', function(event, url, options, data, e) {
            $(e.target).parents('.popover').first().trigger('modal-close');
        });

        this.builders(list.actionBuilders());
    }
});

creme.lv_widget.ListViewActionBuilders = creme.action.DefaultActionBuilderRegistry.sub({
    _init_: function(list) {
        this._list = list;
        this._super_(creme.action.DefaultActionBuilderRegistry, '_init_');
    },

    _defaultDialogOptions: function(url, title) {
        var width = $(window).innerWidth();

        return {
            resizable: true,
            draggable: true,
            width: width * 0.8,
            maxWidth: width,
            url: url,
            title: title
        };
    },

    _build_popover: function(url, options, data, e) {
        var link = $(e.target).closest('[data-action]');
        return creme.dialog.PopoverAction.fromTarget(link, options);
    },

    _build_update: function(url, options, data, e) {
        var list = this._list;
        return this._postQueryAction(url, options, data).onDone(function() {
            list.reload();
        });
    },

    _build_delete: function(url, options, data, e) {
        return this._build_update(url, $.extend({}, options, {
            confirm: gettext('Are you sure?')
        }), data, e);
    },

    _build_form: function(url, options, data, e) {
        var list = this._list;
        options = $.extend(this._defaultDialogOptions(url), options || {});

        return new creme.dialog.FormDialogAction(options, {
            'form-success': function() {
                list.reload();
             }
        });
    },

    _build_clone: function(url, options, data, e) {
        options = $.extend({
            confirm: gettext('Do you really want to clone this entity?')
        }, options || {});

        var action = this._postQueryAction(url, options, data);
        action.onDone(function(event, data, xhr) {
            creme.utils.goTo(data);
        });

        return action;
    },

    _build_edit_selection: function(url, options, data, e) {
        return new creme.lv_widget.EditSelectedAction(this._list, {url: url});
    },

    _build_delete_selection: function(url, options, data, e) {
        return new creme.lv_widget.DeleteSelectedAction(this._list, {url: url});
    },

    _build_addto_selection: function(url, options, data, e) {
        return new creme.lv_widget.AddToSelectedAction(this._list, {url: url});
    },

    _build_merge_selection: function(url, options, data, e) {
        return new creme.lv_widget.MergeSelectedAction(this._list, {url: url});
    },

    _build_submit_lv_state: function(url, options, data, e) {
        var listview = this._list;

        return new creme.component.Action(function() {
            listview.submitState(data, {
                done: function() { this.done(); },
                fail: function() { this.fail(); },
                cancel: function() { this.cancel(); }
            });
        });
    },

    _build_reset_lv_search: function(url, options, data, e) {
        var listview = this._list;

        return new creme.component.Action(function() {
            listview.resetSearchState({
                done: function() { this.done(); },
                fail: function() { this.fail(); },
                cancel: function() { this.cancel(); }
            });
        });
    },

    _build_export_as: function(url, options, data, e) {
        return new creme.lv_widget.ExportAction(this._list, Object.assign({
            url: url
        }, options));
    },

    _build_redirect: function(url, options, data) {
        return this._redirectAction(url, options, data);
    }
});

creme.lv_widget.ListViewHeader = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            standalone: false,
            headTop: 0
        }, options || {});

        this._isStandalone = options.standalone;
        this._headTop = options.headTop;

        this._rowListeners = {
            mouseenter: this._onEnterSelectableRow.bind(this),
            mouseleave: this._onLeaveSelectableRow.bind(this),
            selection: this._onRowSelectionChange.bind(this)
        };
        this._floatListeners = {
            floatHead: this._onHeadFloatEnabled.bind(this)
        };
        this._documentListeners = {
            scroll: this._onDocumentScroll.bind(this)
        };
    },

    isBound: function() {
        return this._list !== undefined;
    },

    _onEnterSelectableRow: function(e) {
        this._list.addClass('first-row-hovered');

        if (this._isStandalone) {
            $('.listview.floatThead-table').addClass('first-row-hovered');
        }
    },

    _onLeaveSelectableRow: function(e) {
        this._list.removeClass('first-row-hovered');

        if (this._isStandalone) {
            $('.listview.floatThead-table').removeClass('first-row-hovered');
        }
    },

    _onRowSelectionChange: function(e, data) {
        this._list.toggleClass('first-row-selected', data.selected);

        if (this._isStandalone) {
            $('.listview.floatThead-table').toggleClass('first-row-selected', data.selected);
        }
    },

    _onHeadFloatEnabled: function(e, isFloated, container) {
        if (isFloated) {
            container.addClass('floated');
            this._list.addClass('floated');

            // vertical constraint 2 : close header actions popovers when they would collide with the floating header scrolling
            $('.header-actions-popover').trigger('modal-close');
        } else {
            container.removeClass('floated');
            this._list.removeClass('floated');
        }
    },

    _onDocumentScroll: function(e) {
        this.updateAnchorPosition();
    },

    bind: function(list) {
        if (this.isBound()) {
            throw new Error('ListViewHeader is already bound');
        }

        var isStandalone = this._isStandalone;
        var headTop = this._headTop;
        this._list = list;

        // handle selection and hover border on floating header so that the first row is correctly styled
        this._list.on('mouseenter', 'tr.selectable:first-child', this._rowListeners.mouseenter);
        this._list.on('mouseleave', 'tr.selectable:first-child', this._rowListeners.mouseleave);
        this._list.on('row-selection-changed', 'tbody tr:first-child', this._rowListeners.selection);

        // listview-popups have no floatThead, stickiness, vertical constraints etc
        if (isStandalone) {
            list.floatThead({
                top: headTop,
                zIndex: 97, // under the popups overlays, under the popovers and their glasspanes
                scrollContainer: function (table) {
                    return table.closest('.sub_content');
                }
            });

            var floatContainer = $('.floatThead-container');
            var isFloating = $(document).scrollTop() > list.offset().top;

            // when the page is loaded and the scrollbar is already scrolled past the header, notify it is already floated
            if (isFloating) {
                floatContainer.addClass('floated');
                list.addClass('floated');
            }

            // or when the floatThead script floats it automatically
            list.on('floatThead', this._floatListeners.floatHead);

            // the anchor will hold the header shadow
            var anchor = this._floatAnchor = $('<div class="floated-header-anchor">');
            anchor.insertAfter(floatContainer)
                  .css({
                      'position': 'fixed'
                  });

            this.updateAnchorPosition();

            $(document).on('scroll', this._documentListeners.scroll);
        }

        return this;
    },

    unbind: function() {
        if (this.isBound() === false) {
            throw new Error('ListViewHeader is not bound');
        }

        this._list.off('mouseenter', 'tr.selectable:first-child', this._rowListeners.mouseenter);
        this._list.off('mouseleave', 'tr.selectable:first-child', this._rowListeners.mouseleave);
        this._list.off('row-selection-changed', 'tbody tr:first-child', this._rowListeners.selection);

        if (this._isStandalone) {
            this._floatAnchor.detach();
            this._list.off('floatThead', this._floatListeners.floatHead);
            $(document).on('scroll', this._documentListeners.scroll);
        }

        this._floatAnchor = undefined;
        this._list = undefined;

        return this;
    },

    updateAnchorPosition: function() {
        if (this._isStandalone) {
            var scrollLeft = $(document).scrollLeft();
            var viewportWidth = $(window).width();

            // complex stickiness between two absolute values modeled as position: fixed over the viewport
            var listAnchorStickingStart = this._list.offset().left;
            var listAnchorStickingEnd = listAnchorStickingStart + this._list.width();

            var overShooting = scrollLeft + viewportWidth >= listAnchorStickingEnd;
            var overshoot = Math.abs(Math.ceil(listAnchorStickingEnd - viewportWidth - scrollLeft));

            var floatContainer = $('.floatThead-container');
            var headerHeight = $(floatContainer.children().get(0)).height(); // we use the height of the contained table because it excludes its own padding
            var anchorHeight = this._floatAnchor.height();

            this._floatAnchor.css({
                'left': Math.max(0, listAnchorStickingStart - scrollLeft),
                'right': overShooting ? overshoot : 0,
                // NB it would be great if we could get the bottom of '.floatThead-container' & set the same bottom to the anchor...
                // 'top': 35 /* menu height */ + $('.floatThead-container').innerHeight() - 4 /* padding + borders */ - 10 /* shadow height */
                'top': this._headTop + headerHeight - anchorHeight
            });
        }
    }
});

creme.lv_widget.ListViewLauncher = creme.widget.declare('ui-creme-listview', {
    options: {
        'selection-mode': 'single',
        'reload-url': ''
    },

    _destroy: function(element) {
        $(document).off('scroll', this._scrollListener);
        element.list_view('destroy');
        element.removeClass('widget-ready');
    },

    _create: function(element, options, cb, sync, args) {
        var selectionMode = options.selectionMode || element.attr('selection-mode');
        var list = this._list = element.find('.listview');

        this._isStandalone = list.hasClass('listview-standalone');
        this._pager = new creme.list.Pager();
        this._header = new creme.lv_widget.ListViewHeader({
            standalone: this._isStandalone,
            headTop: $('.header-menu').height()
        });

        this._rowCount = parseInt(list.attr('data-total-count'));
        this._rowCount = isNaN(this._rowCount) ? 0 : this._rowCount;

        this._scrollListener = this._onDocumentScroll.bind(this);

        // handle popup differentiation
        if (this._isStandalone) {
            element.addClass('ui-creme-listview-standalone');
            $(document).on('scroll', this._scrollListener);
            this._handleHorizontalStickiness();
        } else {
            element.addClass('ui-creme-listview-popup');
        }

        var controller = this._initController(element, {
            selectionMode: selectionMode,
            reloadurl: options['reload-url']
        });

        // only hook up list behavior when there are rows
        if (this._rowCount > 0) {
            if (!this._isStandalone) {
                // pagination in popups
                var popup = element.parents('.ui-dialog').first();
                list.find('.list-footer-container').css('max-width', popup.width());
            } else {
                // left/right in standalone mode
                this._handleHorizontalStickiness();
            }

            this._header.bind(list);
            this._pager.on('refresh', function(event, page) {
                            controller.submitState({page: page});
                        })
                       .bind(list.find('.listview-pagination'));
        }

        element.on('change', '.list-control-group.list-views select', function() {
            controller.submitState({hfilter: $(this).val()});
        });

        element.on('change', '.list-control-group.list-filters select', function() {
            controller.submitState({filter: $(this).val()});
        });

        list.on('change', 'select.list-pagesize-selector', function() {
            controller.submitState({rows: $(this).val()});
        });
    },

    _initController: function(element, options) {
        var listview = this.controller(element);

        // Only init the $.fn.list_view once per form, not on every listview reload
        if (!listview) {
            var inPopup = element.parents('.ui-dialog-content').first().length > 0;
            var reloadUrl = options.reloadurl || window.location.href;

            listview = element.list_view({
                selectionMode: options.selectionMode,
                reloadUrl:     reloadUrl
            });

            if (inPopup === false) {
                listview.on('submit-state-complete', function(event, url, data) {
                    creme.history.push(url);
                });
            }
        }

        return listview;
    },

    _onDocumentScroll: function(e) {
        this._handleHorizontalStickiness();
        this._handleActionPopoverConstraints();
    },

    _handleHorizontalStickiness: function() {
        var scrollLeft = $(document).scrollLeft();
        // Simple stickiness to left: 0
        $('.sticky-container-standalone .sticks-horizontally, .listview-standalone .sticks-horizontally, .footer, .page-decoration').css('transform', 'translateX(' + scrollLeft + 'px)');
    },

    _handleActionPopoverConstraints: function() {
        $('.listview-actions-popover').each(function() {
            var popover = $(this);
            var offset = popover.offset();

            var floatContainer = $('.floatThead-container');
            var floatingOffset = floatContainer.offset();

            // Check for collisions
            if (offset.top < floatingOffset.top + floatContainer.innerHeight() + 5/* safe zone */) {
                var isRowPopover = popover.hasClass('row-actions-popover');
                var isHeaderPopover = popover.hasClass('header-actions-popover');
                var containerIsFloating = floatContainer.hasClass('floated');

                // Vertical constraint 1 : close row actions popovers when they collide with the floating header
                // Vertical constraint 3 : close header actions popovers when they are opened while the header is floating, and the document is scrolled
                var popoverNeedsClosing = isRowPopover || (isHeaderPopover && containerIsFloating);
                if (popoverNeedsClosing) {
                    popover.trigger('modal-close');
                }
            }
        });
    },

    isStandalone: function(element) {
        return this._isStandalone;
    },

    count: function(element) {
        return this._rowCount;
    },

    header: function(element) {
        return this._header;
    },

    pager: function(element) {
        return this._pager;
    },

    controller: function(element) {
        return element.list_view('instance');
    }
});

}(jQuery));
