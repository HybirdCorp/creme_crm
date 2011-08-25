/* jQuery Image Magnify script v1.0
* Last updated: July 13th, 2009. This notice must stay intact for usage
* Author: Dynamic Drive at http://www.dynamicdrive.com/
* Visit http://www.dynamicdrive.com/ for full source code
*/

//jQuery.noConflict()

jQuery.imageMagnifier={
	dsettings: {
		magnifyby: 5, //default increase factor of enlarged image
		duration: 500, //default duration of animation, in millisec
		imgopacity: 0.2 //opacify of original image when enlarged image overlays it
 	},
	cursorcss: 'url(' + creme_media_url("images/magnify.cur") + '), -moz-zoom-in', //Value for CSS's 'cursor' attribute, added to original image
	zIndexcounter: 1100,
	imgshells: [],

	refreshoffsets:function($window, $target, warpshell){
		var $offsets=$target.offset()
		var winattrs={x:$window.scrollLeft(), y:$window.scrollTop(), w:$window.width(), h:$window.height()}
		warpshell.attrs.x=$offsets.left //update x position of original image relative to page
		warpshell.attrs.y=$offsets.top
		warpshell.newattrs.x=winattrs.x+winattrs.w/2-warpshell.newattrs.w/2
		warpshell.newattrs.y=winattrs.y+winattrs.h/2-warpshell.newattrs.h/2
		if (warpshell.newattrs.x<winattrs.x+5){ //no space to the left?
			warpshell.newattrs.x=winattrs.x+5
		}
		else if (warpshell.newattrs.x+warpshell.newattrs.w > winattrs.x+winattrs.w){//no space to the right?
			warpshell.newattrs.x=winattrs.x+5
		}
		if (warpshell.newattrs.y<winattrs.y+5){ //no space at the top?
			warpshell.newattrs.y=winattrs.y+5
		}
	},

	magnify:function($, $target, options){
		var setting={} //create blank object to store combined settings
		var setting=jQuery.extend(setting, this.dsettings, options)
		var effectpos=this.imgshells.length
		var attrs={w:$target.outerWidth(), h:$target.outerHeight()}
		var newattrs={w:Math.round(attrs.w*setting.magnifyby), h:Math.round(attrs.h*setting.magnifyby)}
		$target.css('cursor', jQuery.imageMagnifier.cursorcss)
		var $clone=$target.clone().css({position:'absolute', left:0, top:0, visibility:'hidden', border:'1px solid gray', cursor:'pointer'}).appendTo(document.body)
		$target.add($clone).data('pos', effectpos) //save position of image
		this.imgshells.push({$target:$target, $clone:$clone, attrs:attrs, newattrs:newattrs}) //remember info about this warp image instance
		$target.bind('click.magnify', function(e){ //action when original image is clicked on
			var $this=$(this).css({opacity:setting.imgopacity})
			var imageinfo=jQuery.imageMagnifier.imgshells[$this.data('pos')]
			jQuery.imageMagnifier.refreshoffsets($(window), $this, imageinfo) //refresh offset positions of original and warped images
			var $clone=imageinfo.$clone
			$clone.stop().css({zIndex:++jQuery.imageMagnifier.zIndexcounter, left:imageinfo.attrs.x, top:imageinfo.attrs.y, width:imageinfo.attrs.w, height:imageinfo.attrs.h, opacity:0, visibility:'visible'})
			.animate({opacity:1, left:imageinfo.newattrs.x, top:imageinfo.newattrs.y, width:imageinfo.newattrs.w, height:imageinfo.newattrs.h}, setting.duration,
			function(){ //callback function after warping is complete
				//none added
			}) //end animate
		}) //end click
		$clone.click(function(e){ //action when magnified image is clicked on
			var $this=$(this)
			var imageinfo=jQuery.imageMagnifier.imgshells[$this.data('pos')]
			jQuery.imageMagnifier.refreshoffsets($(window), imageinfo.$target, imageinfo) //refresh offset positions of original and warped images
			$this.stop().animate({opacity:0, left:imageinfo.attrs.x, top:imageinfo.attrs.y, width:imageinfo.attrs.w, height:imageinfo.attrs.h},  setting.duration,
			function(){
				$this.hide()
				imageinfo.$target.css({opacity:1}) //reveal original image
			}) //end animate
		}) //end click
	}
};

jQuery.fn.imageMagnifier=function(options){
	var $=jQuery
	return this.each(function(){ //return jQuery obj
		var $imgref=$(this)
		if (this.tagName!="IMG")
			return true //skip to next matched element
		if (parseInt($imgref.css('width'))>0 && parseInt($imgref.css('height'))>0){ //if image has explicit width/height attrs defined
			jQuery.imageMagnifier.magnify($, $imgref, options)
		}
		else if (this.complete){ //account for IE not firing image.onload
			jQuery.imageMagnifier.magnify($, $imgref, options)
		}
		else{
			$(this).bind('load', function(){
				jQuery.imageMagnifier.magnify($, $imgref, options)
			})
		}
	})
};

//** The following applies the magnify effect to images with class="magnify" and optional "data-magnifyby" and "data-magnifyduration" attrs
//** It also looks for links with attr rel="magnify[targetimageid]" and makes them togglers for that image
/*
jQuery(document).ready(function($){
	var $targets=$('.magnify')
	$targets.each(function(i){
		var $target=$(this)
		var options={}
		if ($target.attr('data-magnifyby'))
			options.magnifyby=parseFloat($target.attr('data-magnifyby'))
		if ($target.attr('data-magnifyduration'))
			options.duration=parseInt($target.attr('data-magnifyduration'))
		$target.imageMagnifier(options)
	})
	var $triggers=$('a[rel^="magnify["]')
	$triggers.each(function(i){
		var $trigger=$(this)
		var targetid=$trigger.attr('rel').match(/\[.+\]/)[0].replace(/[\[\]']/g, '') //parse 'id' from rel='magnify[id]'
		$trigger.data('magnifyimageid', targetid)
		$trigger.click(function(e){
			$('#'+$(this).data('magnifyimageid')).trigger('click.magnify')
			e.preventDefault()
		})
	})
})*/

function initMagnify($selector)
{
    /* jQuery Image Magnify script v1.0
    * Last updated: July 13th, 2009. This notice must stay intact for usage
    * Author: Dynamic Drive at http://www.dynamicdrive.com/
    * Visit http://www.dynamicdrive.com/ for full source code
    */
   var $targets=$($selector);
    $targets.each(function(i){
        var $target=$(this)
        var options={}
        if ($target.attr('data-magnifyby'))
            options.magnifyby=parseFloat($target.attr('data-magnifyby'))
        if ($target.attr('data-magnifyduration'))
            options.duration=parseInt($target.attr('data-magnifyduration'))
        $target.imageMagnifier(options)
    });
    var $triggers=$('a[rel^="magnify["]');
    $triggers.each(function(i){
        var $trigger=$(this)
        var targetid=$trigger.attr('rel').match(/\[.+\]/)[0].replace(/[\[\]']/g, '') //parse 'id' from rel='magnify[id]'
        $trigger.data('magnifyimageid', targetid)
        $trigger.click(function(e){
            $('#'+$(this).data('magnifyimageid')).trigger('click.magnify')
            e.preventDefault()
        });
    });
    /* End of Image Magnify script v1.0 */
}

