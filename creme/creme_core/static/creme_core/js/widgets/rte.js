/*
* jQuery RTE plugin 0.5.1 - create a rich text form for Mozilla, Opera, Safari and Internet Explorer
*
* Copyright (c) 2009 Batiste Bieler
* Distributed under the GPL Licenses.
* Distributed under the The MIT License.
*/

// define the rte light plugin
(function($) {

    $.fn.rte = function(options) {

    $.fn.rte.html = function(iframe) {
        return iframe.contentWindow.document.getElementsByTagName("body")[0].innerHTML;
    };

    $.fn.rte.defaults = {
//         media_url: "/site_media/images",
//         content_css_url: "rte.css",
        dot_net_button_class: null,
        max_height: 350
    };

    // build main options before element iteration
    var opts = $.extend($.fn.rte.defaults, options);

    // iterate and construct the RTEs
    return this.each( function() {

        var textarea = $(this);
        var iframe;
        var element_id = textarea.attr("id");

        // enable design mode
        function enableDesignMode() {

            var content = textarea.val();

            // Mozilla needs this to display caret
            if($.trim(content)=='') {
                content = '<br />';
            }

            // already created? show/hide
            if(iframe) {
                textarea.hide();
                $(iframe).contents().find("body").html(content);
                $(iframe).show();
                $("#toolbar-" + element_id).remove();
                textarea.before(toolbar());

                //beware: several 'return' statements -> duplicated this code ???
                $('#' + element_id + '_is_rte_enabled').attr('checked', true);

                return true;
            }

            // for compatibility reasons, need to be created this way
            iframe = document.createElement("iframe");
            iframe.frameBorder=0;
            iframe.frameMargin=0;
            iframe.framePadding=0;
            iframe.height=200;
            if(textarea.attr('class'))
                iframe.className = textarea.attr('class');
            if(textarea.attr('id'))
                iframe.id = element_id;
            if(textarea.attr('name'))
                iframe.title = textarea.attr('name');

            textarea.after(iframe);

//             var css = "";
//             if(opts.content_css_url) {
//                 css = "<link type='text/css' rel='stylesheet' href='" + opts.content_css_url + "' />";
//             }
//             css = "<link type='text/css' rel='stylesheet' href='" + media_url('main.css') + "' />"; //seems useless

//             var doc = "<html><head>"+css+"</head><body class='frameBody'>"+content+"</body></html>";
            var doc = "<html><head></head><body class='frameBody'>"+content+"</body></html>";
            tryEnableDesignMode(doc, function() {
                $("#toolbar-" + element_id).remove();
                textarea.before(toolbar());
                textarea.hide();
            });

        }

        function tryEnableDesignMode(doc, callback) {
            if(!iframe) { return false; }

            try {
                iframe.contentWindow.document.open();
                iframe.contentWindow.document.write(doc);
                iframe.contentWindow.document.close();
            } catch(error) {
                //console.log(error);
            }
            if (document.contentEditable) {
                iframe.contentWindow.document.designMode = "On";
                callback();
                return true;
            }
            else if (document.designMode != null) {
                try {
                    iframe.contentWindow.document.designMode = "on";
                    callback();
                    return true;
                } catch (error) {
                    //console.log(error);
                }
            }
            setTimeout(function(){tryEnableDesignMode(doc, callback)}, 500);
            return false;
        }

        function disableDesignMode(submit) {
            var content = $(iframe).contents().find("body").html();

            if($(iframe).is(":visible")) {
                textarea.val(content);
            }

            if(submit != true) {
                textarea.show();
                $(iframe).hide();

                $('#' + element_id + '_is_rte_enabled').attr('checked', false);
            }
        }

        function showDialog(node_id, text, title, ok_callback) {
                var $node = $('#'+node_id);
                $node.html(text);
                $node.dialog({
                    buttons: {
                               "Annuler": function() {  $(this).html(""); $(this).dialog("destroy"); },
                               "Ok": function() {  if(ok_callback) ok_callback.apply(null,[$(this)]); $(this).html(""); $(this).dialog("destroy"); }
                    },
                    resize: function(event, ui) {
                        var height = $(this).height();
                        var width = $(this).width();
                        var $textarea = ui.element.find('textarea');
                        $textarea.height(height);
                        $textarea.width(width);
                    },
                    closeOnEscape: false,
                    hide: 'slide',
                    show: 'slide',
                    title: title,
                    modal: true
                });
        }

        // create toolbar and bind events to it's elements
        function toolbar() {
            var tb = $("<div class='rte-toolbar' id='toolbar-"+ element_id +"'><div>\
                <p>\
                    <select>\
                        <option value=''>Block style</option>\
                        <option value='p'>Paragraph</option>\
                        <option value='h3'>Title</option>\
                        <option value='address'>Address</option>\
                    </select>\
                </p>\
                <p>\
                    <a href='#' class='bold'><img src='" + media_url('images/rte/bold.gif') + "' alt='bold' title='bold' /></a>\
                    <a href='#' class='italic'><img src='" + media_url('images/rte/italic.gif') + "' alt='italic' title='italic' /></a>\
                </p>\
                <p>\
                    <a href='#' class='unorderedlist'><img src='" + media_url('images/rte/unordered.gif') + "' alt='unordered list' title='unordered list' /></a>\
                    <a href='#' class='link'><img src='" + media_url('images/web_22.png') + "' alt='link' title='link'/></a>\
                    <a href='#' class='image'><img src='" + media_url('images/image_22.png') + "' alt='image' title='image' /></a>\
                    <a href='#' class='disable'><img src='" +  media_url('images/cancel_22.png')  + "' alt='close rte' title='close rich text editor'/></a>\
                    <a href='#' class='word'><img src='" + media_url('images/document_doc_22.png') + "' alt='word' title='from word'/></a>\
                </p></div></div>");

            $('select', tb).change(function(){
                var index = this.selectedIndex;
                if( index!=0 ) {
                    var selected = this.options[index].value;
                    formatText("formatblock", '<'+selected+'>');
                }
            });
            $('.bold', tb).click(function(){ formatText('bold');return false; });
            $('.italic', tb).click(function(){ formatText('italic');return false; });
            $('.unorderedlist', tb).click(function(){ formatText('insertunorderedlist');return false; });
            $('.link', tb).click(function(){
                var p=prompt("URL:");
                if(p)
                    formatText('CreateLink', p);
                return false; });

            $('.image', tb).click(function(){
                var p=prompt("image URL:");
                if(p)
                    formatText('InsertImage', p);
                return false; });

            $('.disable', tb).click(function() {
                disableDesignMode();
                var edm = $('<a class="rte-edm" href="#">Enable design mode</a>');
                tb.empty().append(edm);
                edm.click(function(e){
                    e.preventDefault();
                    enableDesignMode();
                    // remove, for good measure
                    $(this).remove();
                });
                return false;
            });


            $('.word', tb).click(function() {
                var $dialogArea = $('<div></div>').attr('id','paste_word');
                var $textarea = $('<textarea></textarea>').attr('name','pasted_code').attr('id','pasted_code');
                $(iframe).parents('body').append($dialogArea);

                var word_callback = function($node)
                {
                    var cleaned_value = cleanWord($node.find('textarea').val());
                    var old = $(iframe).contents().find("body").html();
                    $(iframe).contents().find("body").html(old+cleaned_value);
                }

                showDialog('paste_word', $textarea,  "Collez votre texte", word_callback);
                return false;
            });

            // .NET compatability
            if(opts.dot_net_button_class) {
                var dot_net_button = $(iframe).parents('form').find(opts.dot_net_button_class);
                dot_net_button.click(function() {
                    disableDesignMode(true);
                });
            // Regular forms
            } else {
                $(iframe).parents('form').submit(function(){
                    disableDesignMode(true);
                });
            }

            var iframeDoc = $(iframe.contentWindow.document);

            var select = $('select', tb)[0];
            iframeDoc.mouseup(function(){
                setSelectedType(getSelectionElement(), select);
                return true;
            });

            iframeDoc.keyup(function() {
                setSelectedType(getSelectionElement(), select);
                var body = $('body', iframeDoc);
                if(body.scrollTop() > 0) {
                    var iframe_height = parseInt(iframe.style['height'])
                    if(isNaN(iframe_height))
                        iframe_height = 0;
                    var h = Math.min(opts.max_height, iframe_height+body.scrollTop()) + 'px';
                    iframe.style['height'] = h;
                }
                return true;
            });

            return tb;
        };

        function cleanWord( html )
		{
            /* This code has been pasted from ckeditor see legals mentions below */
            ﻿/*
                Copyright (c) 2003-2009, CKSource - Frederico Knabben. All rights reserved.
                For licensing, see LICENSE.html or http://ckeditor.com/license
            */


			// Remove comments [SF BUG-1481861].
			html = html.replace(/<\!--[\s\S]*?-->/g, '' ) ;

			html = html.replace(/<o:p>\s*<\/o:p>/g, '') ;
			html = html.replace(/<o:p>[\s\S]*?<\/o:p>/g, '&nbsp;') ;

			// Remove mso-xxx styles.
			html = html.replace( /\s*mso-[^:]+:[^;"]+;?/gi, '' ) ;

			// Remove margin styles.
			html = html.replace( /\s*MARGIN: 0(?:cm|in) 0(?:cm|in) 0pt\s*;/gi, '' ) ;
			html = html.replace( /\s*MARGIN: 0(?:cm|in) 0(?:cm|in) 0pt\s*"/gi, "\"" ) ;

			html = html.replace( /\s*TEXT-INDENT: 0cm\s*;/gi, '' ) ;
			html = html.replace( /\s*TEXT-INDENT: 0cm\s*"/gi, "\"" ) ;

			html = html.replace( /\s*TEXT-ALIGN: [^\s;]+;?"/gi, "\"" ) ;

			html = html.replace( /\s*PAGE-BREAK-BEFORE: [^\s;]+;?"/gi, "\"" ) ;

			html = html.replace( /\s*FONT-VARIANT: [^\s;]+;?"/gi, "\"" ) ;

			html = html.replace( /\s*tab-stops:[^;"]*;?/gi, '' ) ;
			html = html.replace( /\s*tab-stops:[^"]*/gi, '' ) ;

			// Remove FONT face attributes.
			/*if ( ignoreFont )
			{*/
				html = html.replace( /\s*face="[^"]*"/gi, '' ) ;
				html = html.replace( /\s*face=[^ >]*/gi, '' ) ;

				html = html.replace( /\s*FONT-FAMILY:[^;"]*;?/gi, '' ) ;
			//}

			// Remove Class attributes
			html = html.replace(/<(\w[^>]*) class=([^ |>]*)([^>]*)/gi, "<$1$3") ;

			// Remove styles.
			//if ( removeStyles )
				html = html.replace( /<(\w[^>]*) style="([^\"]*)"([^>]*)/gi, "<$1$3" ) ;

			// Remove style, meta and link tags
			html = html.replace( /<STYLE[^>]*>[\s\S]*?<\/STYLE[^>]*>/gi, '' ) ;
			html = html.replace( /<(?:META|LINK)[^>]*>\s*/gi, '' ) ;

			// Remove empty styles.
			html =  html.replace( /\s*style="\s*"/gi, '' ) ;

			html = html.replace( /<SPAN\s*[^>]*>\s*&nbsp;\s*<\/SPAN>/gi, '&nbsp;' ) ;

			html = html.replace( /<SPAN\s*[^>]*><\/SPAN>/gi, '' ) ;

			// Remove Lang attributes
			html = html.replace(/<(\w[^>]*) lang=([^ |>]*)([^>]*)/gi, "<$1$3") ;

			html = html.replace( /<SPAN\s*>([\s\S]*?)<\/SPAN>/gi, '$1' ) ;

			html = html.replace( /<FONT\s*>([\s\S]*?)<\/FONT>/gi, '$1' ) ;

			// Remove XML elements and declarations
			html = html.replace(/<\\?\?xml[^>]*>/gi, '' ) ;

			// Remove w: tags with contents.
			html = html.replace( /<w:[^>]*>[\s\S]*?<\/w:[^>]*>/gi, '' ) ;

			// Remove Tags with XML namespace declarations: <o:p><\/o:p>
			html = html.replace(/<\/?\w+:[^>]*>/gi, '' ) ;

			html = html.replace( /<(U|I|STRIKE)>&nbsp;<\/\1>/g, '&nbsp;' ) ;

			html = html.replace( /<H\d>\s*<\/H\d>/gi, '' ) ;

			// Remove "display:none" tags.
			html = html.replace( /<(\w+)[^>]*\sstyle="[^"]*DISPLAY\s?:\s?none[\s\S]*?<\/\1>/ig, '' ) ;

			// Remove language tags
			html = html.replace( /<(\w[^>]*) language=([^ |>]*)([^>]*)/gi, "<$1$3") ;

			// Remove onmouseover and onmouseout events (from MS Word comments effect)
			html = html.replace( /<(\w[^>]*) onmouseover="([^\"]*)"([^>]*)/gi, "<$1$3") ;
			html = html.replace( /<(\w[^>]*) onmouseout="([^\"]*)"([^>]*)/gi, "<$1$3") ;

			/*if ( editor.config.pasteFromWordKeepsStructure )
			{
				// The original <Hn> tag send from Word is something like this: <Hn style="margin-top:0px;margin-bottom:0px">
				html = html.replace( /<H(\d)([^>]*)>/gi, '<h$1>' ) ;

				// Word likes to insert extra <font> tags, when using MSIE. (Wierd).
				html = html.replace( /<(H\d)><FONT[^>]*>([\s\S]*?)<\/FONT><\/\1>/gi, '<$1>$2<\/$1>' );
				html = html.replace( /<(H\d)><EM>([\s\S]*?)<\/EM><\/\1>/gi, '<$1>$2<\/$1>' );
			}
			else
			{*/
				html = html.replace( /<H1([^>]*)>/gi, '<div$1><b><font size="6">' ) ;
				html = html.replace( /<H2([^>]*)>/gi, '<div$1><b><font size="5">' ) ;
				html = html.replace( /<H3([^>]*)>/gi, '<div$1><b><font size="4">' ) ;
				html = html.replace( /<H4([^>]*)>/gi, '<div$1><b><font size="3">' ) ;
				html = html.replace( /<H5([^>]*)>/gi, '<div$1><b><font size="2">' ) ;
				html = html.replace( /<H6([^>]*)>/gi, '<div$1><b><font size="1">' ) ;

				html = html.replace( /<\/H\d>/gi, '<\/font><\/b><\/div>' ) ;

				// Transform <P> to <DIV>
				var re = new RegExp( '(<P)([^>]*>[\\s\\S]*?)(<\/P>)', 'gi' ) ;	// Different because of a IE 5.0 error
				html = html.replace( re, '<div$2<\/div>' ) ;

				// Remove empty tags (three times, just to be sure).
				// This also removes any empty anchor
				html = html.replace( /<([^\s>]+)(\s[^>]*)?>\s*<\/\1>/g, '' ) ;
				html = html.replace( /<([^\s>]+)(\s[^>]*)?>\s*<\/\1>/g, '' ) ;
				html = html.replace( /<([^\s>]+)(\s[^>]*)?>\s*<\/\1>/g, '' ) ;
			//}

			return html ;
		}



        function formatText(command, option) {
            iframe.contentWindow.focus();
            try{
                iframe.contentWindow.document.execCommand(command, false, option);
            }catch(e){
                //console.log(e)
            }
            iframe.contentWindow.focus();
        };

        function setSelectedType(node, select) {
            while(node.parentNode) {
                var nName = node.nodeName.toLowerCase();
                for(var i=0;i<select.options.length;i++) {
                    if(nName==select.options[i].value){
                        select.selectedIndex=i;
                        return true;
                    }
                }
                node = node.parentNode;
            }
            select.selectedIndex=0;
            return true;
        };

        function getSelectionElement() {
            if (iframe.contentWindow.document.selection) {
                // IE selections
                selection = iframe.contentWindow.document.selection;
                range = selection.createRange();
                try {
                    node = range.parentElement();
                }
                catch (e) {
                    return false;
                }
            } else {
                // Mozilla selections
                try {
                    selection = iframe.contentWindow.getSelection();
                    range = selection.getRangeAt(0);
                }
                catch(e){
                    return false;
                }
                node = range.commonAncestorContainer;
            }
            return node;
        };

        // enable design mode now
        enableDesignMode();

    }); //return this.each
    
};// rte

})(jQuery);
