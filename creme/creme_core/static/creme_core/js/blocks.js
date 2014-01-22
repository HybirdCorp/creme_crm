/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2009-2014  Hybird

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

creme.blocks = {
    //__registeredBlocks: {},
    collapsed_class:    'collapsed',
    hide_fields_class:  'hide_empty_fields',
    status_stave_delay: 500
};

/*
creme.blocks.register = function(block_id) {
    var $block = $(block_id);

    if ($block.size() == 1) {
        this.__registeredBlocks[block_id] = $block;
    } else {
        console.log('creme.blocks.register::block_id is not unique:' + block_id);
    }
};

creme.blocks.get_block = function(block_id) {
    return this.__registeredBlocks[block_id];
};
*/

creme.blocks.reload = function(url) {
//     creme.ajax.query(url, {backend: {sync: true, dataType: 'json'}})
    creme.ajax.query(url, {backend: {sync: false, dataType: 'json'}})
//               .onStart(creme.utils.showPageLoadOverlay)
              .onDone(function(event, data) {
                  data.forEach(function(entry) {
                      creme.blocks.fill($('[id="' + entry[0] + '"]'), $(entry[1]));
                  });
               })
//               .onComplete(creme.utils.hidePageLoadOverlay)
              .start();
    /*
    $.ajax({
        url:        url,
        async:      false,
        type:       "GET",
        dataType:   "json",
        cache:      false, // ??
        beforeSend: function() {creme.utils.loading('loading', false);},
        success:    function(data) {
                        for (var i = 0; i < data.length; ++i) {
                            var block_data    = data[i];                  // tuple: (block_name, block_html)
                            var block         = $('#' + block_data[0])
                            var block_content = $(block_data[1]);         // 'compile' to DOM

                            creme.blocks.fill(block, block_content);
                        }
                    },
        complete:   function() {creme.utils.loading('loading', true);}
    });
    */
};

creme.blocks.fill = function(block, content) {
    block.replaceWith(content);
    content.find('.collapser').each(function() {creme.utils.bindTableToggle($(this));});
    creme.blocks.initialize(content);
};

// TODO : make a generic method for deferred save. something like:
//        deferredAction(element, action_name, action_func, action_delay)
creme.blocks.saveState = function(block) {
    var state = {
            is_open:           $(block).hasClass('collapsed') ? 0 : 1,
            show_empty_fields: $(block).hasClass(this.hide_fields_class) ? 0 : 1
    };

    var previous = block.data('block-deferred-save');

    if (previous !== undefined)
        previous.reject();

    var deferred = $.Deferred();

    $.when(deferred.promise()).then(function(status) {
        block.removeData('block-deferred-save');
        creme.ajax.json.post('/creme_core/blocks/reload/set_state/' + block.attr('id') + '/',
                             state, null, null, true);
    }, null, null);

    block.data('block-deferred-save', deferred);

    window.setTimeout(function() {
        deferred.resolve();
    }, this.status_stave_delay);
};

creme.blocks.initEmptyFields = function(block) {
    $('tbody > tr.content').not(':has(> td:not(.edit_inner):not(:empty))', block).addClass('collapsable-field');
    creme.blocks.updateFieldsColors(block);
    creme.blocks.updateToggleButton(block);
};

creme.blocks.updateFieldsColors = function(block) {
    var line_collapsed = block.hasClass(this.hide_fields_class);

    if (!line_collapsed) {
        $('tbody > tr.content:even td', block).toggleClass('block_line_light', true).toggleClass('block_line_dark', false);
        $('tbody > tr.content:odd td', block).toggleClass('block_line_light', false).toggleClass('block_line_dark', true);

        $('tbody > tr.content:even th', block).toggleClass('block_header_line_light', true).toggleClass('block_header_line_dark', false);
        $('tbody > tr.content:odd th', block).toggleClass('block_header_line_light', false).toggleClass('block_header_line_dark', true);
    } else {
        $('tbody > tr.content:not(.collapsable-field):even td', block).toggleClass('block_line_light', true).toggleClass('block_line_dark', false);
        $('tbody > tr.content:not(.collapsable-field):odd td', block).toggleClass('block_line_light', false).toggleClass('block_line_dark', true);

        $('tbody > tr.content:not(.collapsable-field):even th', block).toggleClass('block_header_line_light', true).toggleClass('block_header_line_dark', false);
        $('tbody > tr.content:not(.collapsable-field):odd th', block).toggleClass('block_header_line_light', false).toggleClass('block_header_line_dark', true);
    }
}

creme.blocks.updateToggleButton = function(block, collapsed) {
    var button = $('table.block_header th.actions a.view_more, table.block_header th.actions a.view_less', block);
    var collapsed = block.hasClass(this.hide_fields_class);
    var button_title = collapsed ? gettext('Show empty fields') : gettext('Hide empty fields');

    button.toggleClass('view_less', !collapsed).toggleClass('view_more', collapsed);
    button.attr('title', button_title)
          .attr('alt', button_title);
}

creme.blocks.toggleEmptyFields = function(button) {
    var $block = $(button).parents('table[id!=].table_detail_view:not(.collapsed)');

    if ($block.size() == 0)
        return;

    var previous_state = $block.hasClass(this.hide_fields_class);

    $block.toggleClass(this.hide_fields_class);

    creme.blocks.updateFieldsColors($block);
    creme.blocks.updateToggleButton($block);

    $block.trigger('creme-blocks-field-display-changed', {action : previous_state ? 'show' : 'hide'});
};

creme.blocks.initialize = function(block) {
    block.bind('creme-table-collapse', function(e, params) {
        creme.blocks.saveState($(this));
    });

    block.bind('creme-blocks-field-display-changed', function(e, params) {
        creme.blocks.saveState($(this));
    });

    creme.blocks.initEmptyFields(block);
    creme.widget.ready(block);
};

creme.blocks.bindEvents = function(root) {
    $('.table_detail_view[id]:not(.block-ready)', root).each(function() {
        var block = $(this);

        try {
            creme.blocks.initialize(block);
            block.addClass('block-ready');
        } catch(e) {
            console.warn('unable to initialize block', block.attr('id'), ':', e);
        }
    });

    /*
    var __registeredBlocks = this.__registeredBlocks;

    for (var i in __registeredBlocks) {
        creme.blocks.initialize(__registeredBlocks[i]);
    }
    */
};

creme.blocks.scrollToError = function(block) {
    creme.utils.scrollTo($('.errorlist:first'));
}

creme.blocks.form = function(url, options, data) {
    var options = options || {};
    var dialog = creme.dialogs.form(url, options, data);

    if (options.blockReloadUrl) {
        dialog.onFormSuccess(function() {
                  creme.blocks.reload(options.blockReloadUrl);
               });
    }

    return dialog;
};

creme.blocks.confirmPOSTQuery = function(url, options, data) {
    return creme.blocks.confirmAjaxQuery(url, $.extend({action:'post'}, options), data);
}

creme.blocks.confirmAjaxQuery = function(url, options, data) {
    var action = creme.utils.confirmAjaxQuery(url, options, data);

    if (options.blockReloadUrl) {
        action.onComplete(function(event, data) {
                  creme.blocks.reload(options.blockReloadUrl);
               });
    }

    return action;
};

creme.blocks.ajaxPOSTQuery = function(url, options, data) {
    return creme.blocks.ajaxQuery(url, $.extend({action:'post'}, options), data);
}

creme.blocks.ajaxQuery = function(url, options, data) {
    var query = creme.ajax.query(url, options, data);

    if (options.blockReloadUrl) {
        query.onComplete(function(event, data) {
                 creme.blocks.reload(options.blockReloadUrl);
              });
    }

    return query;
};

// creme.utils.loadBlock = creme.blocks.reload;
