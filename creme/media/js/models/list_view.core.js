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
/*
 * Dependencies : jQuery / jquery.utils.js
 */

//TODO : To be deleted and all console.log in code also
if(!window.console)
{
    window.console = {};
    window.console.log = function(){};
}

(function($) {
    $.fn.list_view = function(options) {

        var isMethodCall = (typeof options == 'string'),
            args = Array.prototype.slice.call(arguments, 1);

        $.fn.list_view.defaults = {
            user_page         : '#user_page',
            selected_rows     : '#selected_rows',
            selectable_class  : 'selectable',
            selected_class    : 'selected',
            id_container      : '[name="entity_id"]',
            checkbox_selector : '[name="select_one"]',
            all_boxes_selector: '[name="select_all"]',
            beforeSubmit      : null,
            afterSubmit       : null,
            o2m               : false,
            entity_separator  : ',',
            serializer : 'input[name!=][type!="submit"], select[name!=]'
        };

        var getters = ["countEntities", "getSelectedEntities",
                                  "getSelectedEntitiesAsArray",
                                  "option", "serializeMe"];

        if (isMethodCall && $.inArray(options, getters) > -1) {

                var instance = $.data(this[0], 'list_view');
                return (instance ? instance[options].apply(instance, args)
                        : undefined);
        }

        return this.each(function() {

            // constructor
            if(!isMethodCall)
            {
                var opts = $.extend($.fn.list_view.defaults, options);
                var selected_ids = [];
                var self = $(this);

                $.data(this, 'list_view', this);

                opts.beforeSubmit = ($.isFunction(opts.beforeSubmit)) ? opts.beforeSubmit : false;
                opts.afterSubmit = ($.isFunction(opts.afterSubmit)) ? opts.afterSubmit : false;
                
                /***************** Getters & Setters *****************/
                this.getSelectedEntities = function(){
                    return $(opts.selected_rows, self).val();
                }

                this.getSelectedEntitiesAsArray = function(){
                    return ($(opts.selected_rows, self).val()!=="") ? $(opts.selected_rows, self).val().split(opts.entity_separator) : [];
                }

                this.countEntities = function(){
                    return ($(opts.selected_rows, self).val()!=="") ? $(opts.selected_rows, self).val().split(opts.entity_separator).length : 0;
                }

                this.option = function(key, value){
                    if (typeof key == "string") {
                        if (value === undefined) {
                            return opts[key];
                        }
                        opts[key] = value;
                    }
                }
                /***************** Helpers ****************************/
                this.reload = function(is_ajax){
                    var submit_opts = {
                        'action': creme.utils.appendInUrl(window.location.href,'?ajax='+is_ajax || true),
                        'success':function(data, status){
                            self.empty().html(data);
                        }
                    };

//                    self.list_view('handleSubmit', null, submit_opts, null);
                    this.handleSubmit(null, submit_opts, null);
                }

                /***************** Row selection part *****************/
                this.enableRowSelection = function(){
                    self.find('.'+opts.selectable_class)
                    //.live('click',
                    .bind('click',
                        function(e){
                            var entity_id = $(this).find(opts.id_container).val();
                            var entity_id_index = $.inArray(entity_id, selected_ids);//selected_ids.indexOf(entity_id);
                            if(!$(this).hasClass(opts.selected_class))
                            {
                                if(entity_id_index === -1){
                                    if(opts.o2m){
                                        selected_ids = [];
                                        self.find('.'+opts.selected_class).removeClass(opts.selected_class);
                                    }
                                    selected_ids.push(entity_id);
                                    $(opts.selected_rows).val(selected_ids.join(opts.entity_separator));
                                }
                                if(!$(this).hasClass(opts.selected_class))$(this).addClass(opts.selected_class);
                                if(!opts.o2m){
                                    $(this).find(opts.checkbox_selector).check();
                                }
                            }
                            else {
                                self.find(opts.all_boxes_selector).uncheck();
                                if(entity_id_index !== -1) selected_ids.splice(entity_id_index, 1);
                                $(opts.selected_rows).val(selected_ids.join(opts.entity_separator));
                                if($(this).hasClass(opts.selected_class))$(this).removeClass(opts.selected_class);
                                if(!opts.o2m){
                                    $(this).find(opts.checkbox_selector).uncheck();
                                }
                            }
                        }
                    );
                }
                /******************************************************/

                /***************** Check all boxes part *****************/
                this.enableCheckAllBoxes = function(){
//                    self.find(opts.all_boxes_selector).live('click',
                    self.find(opts.all_boxes_selector)
                    .bind('click',
                        function(e)
                        {
                            var entities = self.find('.'+opts.selectable_class);
                            if($(this).is(':checked'))
                            {
                                entities.each(function(){
                                    var entity_id = $(this).find(opts.id_container).val();
                                    var entity_id_index = $.inArray(entity_id, selected_ids);//selected_ids.indexOf(entity_id);
                                    if(entity_id_index === -1){
                                        selected_ids.push(entity_id);
                                    }
                                    if(!$(this).hasClass(opts.selected_class))$(this).addClass(opts.selected_class);
                                    if(!opts.o2m){
                                        $(this).find(opts.checkbox_selector).check();
                                    }
                                });
                                $(opts.selected_rows).val(selected_ids.join(opts.entity_separator));
                            }
                            else
                            {
                                entities.each(function(){
                                    if($(this).hasClass(opts.selected_class))$(this).removeClass(opts.selected_class);
                                    if(!opts.o2m){
                                        $(this).find(opts.checkbox_selector).uncheck();
                                    }
                                });
                                selected_ids = [];
                                $(opts.selected_rows).val('');
                            }
                        }
                    );
                }

                /******************************************************/

                /***************** Submit part *****************/

                //Remove this part in ajax lv for handling multi-page selection,
                //if that you want implement the "coloration" selection on submit
                this.flushSelected = function(){
                    $(opts.selected_rows, self).val('');
                    selected_ids = [];
                }

                this.disableEvents = function(){
//                    self.find('.'+opts.selectable_class).die('click');
//                    if(!opts.o2m) self.find(opts.all_boxes_selector).die('click');
                    self.find('.'+opts.selectable_class).unbind('click');
                    if(!opts.o2m) self.find(opts.all_boxes_selector).unbind('click');
                }

                this.enableEvents = function(){
                    this.enableRowSelection();
                    if(!opts.o2m) this.enableCheckAllBoxes();
                }

//                this.serializeMe = function (){
//                    var data = {};
//                    self.find(opts.serializer).each(function(){
//                       var $node = $(this);
//                       data[$node.attr('name')] = $node.val();
//                    });
//                    return data;
//                }
                
                this.serializeMe = function (){
                    var data = {};
                    self.find(opts.serializer).each(function(){
                       var $node = $(this);
                       if(typeof(data[$node.attr('name')]) == "undefined"){
                           data[$node.attr('name')] = [$node.val()];
                       }
                       else if(data[$node.attr('name')].length > 0)
                       {
                           data[$node.attr('name')].push($node.val());
                       }
                    });
                    return data;
                }

                this.handleSubmit = function(form, options, target, extra_data){
                    var data = this.serializeMe();
                    if(typeof(extra_data)!="undefined"){
                        data = $.extend(data, extra_data);
                    }

                    var $target = $(target);
                    data[$target.attr('name')] = $target.val();

                    if(typeof(data['page']) == "undefined")
                    {
                        data['page'] = $(opts.user_page, self);
                    }

                    this.disableEvents();

                    //We get a previous beforeComplete user callback if exists
                    var previousCallback = null;
                    if(typeof(options) !== "undefined" && typeof(options['beforeComplete']) == "function")
                    {
                        previousCallback = options['beforeComplete'];
                    }

                    options['beforeComplete'] = function(request, status){
                        //Calling our beforeComplete callback
                        self.list_view('enableEvents');
                        //Then user callback
                        if(previousCallback) previousCallback(request, status);
                    }
                    
                    creme.ajax.submit(form, data, options);
                    this.flushSelected();
                }

                this.init = function(){
                    this.enableEvents();
                }

                this.init();

            }
            else
            {
                if($.isFunction(this[options])) this[options].apply(this, args);
            }
        });
    };//$.fn.list_view
})(jQuery);

