/**
* GcColor colorpicker plug-in for jQuery
* Originaly written by Stefan Petre <www.eyecon.ro>
* @author Gusts 'gusC' Kaksis <gusts.kaksis@gmail.com>
* @version 1.0.3
*/
(function($){
	var gcColor = function(){
		var defaults = {
			onOpen: function () {},
			onClose: function () {},
			onChange: function ($input, selectedValue) {
			    $input.val(selectedValue);
			    updateTargetColor($input);
                //$input.css('background-color', '#'+selectedValue);
                //changeTextColor($input, selectedValue);
            },
			useButton: true,
			defaultColor: '#FF0000'
		},
		_uiInstalled = (typeof $.ui == 'undefined' ? false : true),
		_dialogBody = '<div id="gccolor-dialog" style="display: none;">'
  		+ '<div id="gccolor-color">'
  		+ '<div>'
  		+ '<div></div>'
  		+ '</div>'
  		+ '</div>'
			+ '<div id="gccolor-hue">'
			+ '<div></div>'
			+ '</div>'
			+ '<div id="gccolor-new-color"></div>'
			+ '<div id="gccolor-current-color"></div>'
			+ '<div id="gccolor-hex"><input type="text" maxlength="6" size="6" /></div>'
			+ '<div id="gccolor-rgb-r" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-rgb-g" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-rgb-b" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-hsb-h" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-hsb-s" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-hsb-b" class="gccolor-field"><input type="text" maxlength="3" size="3" /><span></span></div>'
			+ '<div id="gccolor-submit"></div>'
			+ '</div>',
		_startHue = function(e){
      $(document).data('gccolor').dragItem = {
      	lastX: e.pageX,
      	lastY: e.pageY
			};
			_dragHue(e);
			$(document).bind('mousemove', _dragHue);
			$(document).bind('mouseup', _endHue);
		},
		_dragHue = function(e){
			var item = $('#gccolor-hue');
      var y = e.pageY - item.offset().top;
      if (y < 0){
				y = 0;
			} else if (y > 150){
				y = 150;
			}
			$(document).data('gccolor').hsb.h = 359 - Math.round((y / 150) * 359);
			if (!$.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			} else {
				$('#gccolor-hue div').css('top', y + 'px');
			}
			changeColor();
			return false;
		},
		_endHue= function(e){
      $(document).unbind('mousemove', _dragHue);
			$(document).unbind('mouseup', _endHue);
			$(document).data('gccolor').dragItem = null;
			if ($.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			}
		},
		_startColor = function(e){
			$(document).data('gccolor').dragItem = {
      	lastX: e.pageX,
      	lastY: e.pageY
			};
			_dragColor(e);
			$(document).bind('mousemove', _dragColor);
			$(document).bind('mouseup', _endColor);
		},
		_dragColor = function(e){
			var item = $('#gccolor-color > div');
      var x = e.pageX - item.offset().left;
      var y = e.pageY - item.offset().top;
      if (x < 0){
        x = 0;
			} else if (x > 150){
				x = 150;
			}
			if (y < 0){
				y = 0;
			} else if (y > 150){
				y = 150;
			}
      $(document).data('gccolor').hsb.s = Math.round((x / 150) * 100);
      $(document).data('gccolor').hsb.b = 100 - Math.round((y / 150) * 100);
      if (!$.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			} else {
				$('#gccolor-color > div div').css('top', y + 'px');
				$('#gccolor-color > div div').css('left', x + 'px');
			}
			changeColor();
			return false;
		},
		_endColor = function(e){
			$(document).unbind('mousemove', _dragColor);
			$(document).unbind('mouseup', _endColor);
			$(document).data('gccolor').dragItem = null;
			if ($.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			}
		},
		_startUnit = function(e){
      $(document).data('gccolor').dragItem = {
      	item: $(this),
      	lastX: e.pageX,
      	lastY: e.pageY
			};
			$(document).bind('mousemove', _dragUnit);
			$(document).bind('mouseup', _endUnit);
		},
		_dragUnit = function(e){
			var item = $(document).data('gccolor').dragItem.item;
			var name = item.parent().attr('id')
			var deltaY = e.pageY - $(document).data('gccolor').dragItem.lastY;
			var prevVal = parseInt(item.prev().val());
			var newVal = prevVal;
			if (deltaY < 0){
				newVal = prevVal + 1;
			} else if (deltaY > 0){
				newVal = prevVal - 1;
			}
			if (name == 'gccolor-hsb-h'){
				if (newVal > 359){
					newVal = 0;
				} else if (newVal <= 0){
					newVal = 359;
				}
			} else if (name == 'gccolor-hsb-s' || name == 'gccolor-hsb-b'){
				if (newVal > 100){
					newVal = 100;
				} else if (newVal <= 0){
					newVal = 0;
				}
			} else {
				if (newVal > 255){
					newVal = 255;
				} else if (newVal <= 0){
					newVal = 0;
				}
			}
			var rgb = _HSBtoRGB($(document).data('gccolor').hsb);
			switch (name){
				case 'gccolor-hsb-h':
					$(document).data('gccolor').hsb.h = newVal;
					break;
				case 'gccolor-hsb-s':
					$(document).data('gccolor').hsb.s = newVal;
					break;
				case 'gccolor-hsb-b':
					$(document).data('gccolor').hsb.b = newVal;
					break;
				case 'gccolor-rgb-r':
					rgb.r = newVal;
					$(document).data('gccolor').hsb = _RGBtoHSB(rgb);
					break;
				case 'gccolor-rgb-g':
					rgb.g = newVal;
					$(document).data('gccolor').hsb = _RGBtoHSB(rgb);
					break;
				case 'gccolor-rgb-b':
					rgb.b = newVal;
					$(document).data('gccolor').hsb = _RGBtoHSB(rgb);
					break;
			}
			if (!$.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			}
			changeColor();
			item.prev().val(newVal);
			$(document).data('gccolor').dragItem.lastY = e.pageY;
		},
		_endUnit= function(e){
      $(document).unbind('mousemove', _dragUnit);
			$(document).unbind('mouseup', _endUnit);
			$(document).data('gccolor').dragItem = null;
			if ($.browserInfo().msie){
				_setFromHSB($(document).data('gccolor').hsb);
			}
		},
		_HEXtoRGB = function(hex){
			var hex = parseInt(((hex.indexOf('#') > -1) ? hex.substring(1) : hex), 16);
			return {r: hex >> 16, g: (hex & 0x00FF00) >> 8, b: (hex & 0x0000FF)};
		},
		_HSBtoRGB = function(hsb){
			var b = Math.ceil(hsb.b * 2.55)
			if (hsb.b == 0){
				return {r: 0, g: 0, b: 0};
			} else if (hsb.s == 0){
				return {r: b, g: b, b: b};
			}
			var Hi = Math.floor(hsb.h / 60);
	    var f = hsb.h / 60 - Hi;
	    var p = Math.round(hsb.b * (100 - hsb.s) * 0.0255);
	    var q = Math.round(hsb.b * (100 - f * hsb.s) * 0.0255);
	    var t = Math.round(hsb.b * (100 - (1 - f) * hsb.s) * 0.0255);
	    switch (Hi) {
	      case 0: return {r: b, g: t, b: p}; break;
	      case 1: return {r: q, g: b, b: p}; break;
	      case 2: return {r: p, g: b, b: t}; break;
	      case 3: return {r: p, g: q, b: b}; break;
	      case 4: return {r: t, g: p, b: b}; break;
	      case 5: return {r: b, g: p, b: q}; break;
	    }
			return {r: 0, g: 0, b: 0};
		},
		_RGBtoHSB = function(rgb){
      var hsb = {};
			hsb.b = Math.max(Math.max(rgb.r, rgb.g), rgb.b);
			hsb.s = (hsb.b <= 0) ? 0 : Math.round(100 * (hsb.b - Math.min(Math.min(rgb.r, rgb.g), rgb.b)) / hsb.b);
			hsb.b = Math.round((hsb.b / 255) * 100);
			if((rgb.r == rgb.g) && (rgb.g == rgb.b)) hsb.h = 0;
			else if(rgb.r >= rgb.g && rgb.g >= rgb.b) hsb.h = 60 * (rgb.g - rgb.b) / (rgb.r - rgb.b);
			else if(rgb.g >= rgb.r && rgb.r >= rgb.b) hsb.h = 60  + 60 * (rgb.g - rgb.r) / (rgb.g - rgb.b);
			else if(rgb.g >= rgb.b && rgb.b >= rgb.r) hsb.h = 120 + 60 * (rgb.b - rgb.r) / (rgb.g - rgb.r);
			else if(rgb.b >= rgb.g && rgb.g >= rgb.r) hsb.h = 180 + 60 * (rgb.b - rgb.g) / (rgb.b - rgb.r);
			else if(rgb.b >= rgb.r && rgb.r >= rgb.g) hsb.h = 240 + 60 * (rgb.r - rgb.g) / (rgb.b - rgb.g);
			else if(rgb.r >= rgb.b && rgb.b >= rgb.g) hsb.h = 300 + 60 * (rgb.r - rgb.b) / (rgb.r - rgb.g);
			else hsb.h = 0;
			hsb.h = Math.round(hsb.h);
			return hsb;
		},
		_RGBtoHEX = function(rgb){
      var hex = [
				rgb.r.toString(16),
				rgb.g.toString(16),
				rgb.b.toString(16)
			];
			$.each(hex, function (nr, val) {
				if (val.length == 1) {
					hex[nr] = '0' + val;
				}
			});
			return hex.join('');
		},
		_setFields = function(hsb, rgb, hex){
			$('#gccolor-hsb-h input').val(hsb.h);
			$('#gccolor-hsb-s input').val(hsb.s);
			$('#gccolor-hsb-b input').val(hsb.b);
			$('#gccolor-rgb-r input').val(rgb.r);
			$('#gccolor-rgb-g input').val(rgb.g);
			$('#gccolor-rgb-b input').val(rgb.b);
			$('#gccolor-hex input').val(hex);
			$('#gccolor-new-color').css('background-color', '#' + hex);
			var colorBGhex = _RGBtoHEX(_HSBtoRGB({h: hsb.h, s: 100, b: 100}));
			$('#gccolor-color').css('background-color', '#' + colorBGhex);
			$('#gccolor-color > div div').css('top', (((100 - hsb.b) / 100) * 150) + 'px');
			$('#gccolor-color > div div').css('left', ((hsb.s / 100) * 150) + 'px');
			$('#gccolor-hue div').css('top', (150 - ((hsb.h / 359) * 150)) + 'px');
		},
		_setFromHSB = function(hsb){
			$(document).data('gccolor').hsb = hsb;
			var rgb = _HSBtoRGB(hsb);
			var hex = _RGBtoHEX(rgb);
			_setFields(hsb, rgb, hex);
		},
		_setFromRGB = function(rgb){
			var hex = _RGBtoHEX(rgb);
			var hsb = _RGBtoHSB(rgb);
			$(document).data('gccolor').hsb = hsb;
			_setFields(hsb, rgb, hex);
		},
		_setFromHEX = function(hex){
			var rgb = _HEXtoRGB(hex);
			var hsb = _RGBtoHSB(rgb);
			$(document).data('gccolor').hsb = hsb;
			_setFields(hsb, rgb, hex);
		},
		closeOnEsc = function(e){
			if (e.keyCode == 27){
				$('#gccolor-dialog').hide();
				var data = $(document).data('gccolor');
				closeDialog(data.target, data.options, true);
			}
		},
		closeOnOutsideClick = function(e){
		    if ($('#gccolor-dialog').is(':visible') === false)
		        return;

		    var data = $(document).data('gccolor');
		    var is_target = $(e.target).is(data.target);
		    var is_togglebutton = $(e.target).is(data.target.parent().find("a.gccolor-button:first"));
		    var is_inside = $(e.target).is("#gccolor-dialog") || $(e.target).parents('#gccolor-dialog').length > 0;

		    if (!is_target && !is_togglebutton && !is_inside) {
		        closeDialog(data.target, data.options, false);
		    }
		},
		toggleDialog = function(target, options) {
		    if ($('#gccolor-dialog').is(':visible')) {
		        closeDialog(target, options, false);
		    } else {
		        openDialog(target, options);
		    }
		},
		openDialog = function(target, options){
			$(document).data('gccolor', {
					target: target,
					options: options,
					hsb: {h: 0, s: 100, b: 100},
					dragItem: null
			});
			if (typeof options.onOpen == 'function'){
				options.onOpen(target);
			}
			var hexColor = $(target).val().replace('#','').toUpperCase();
			if (hexColor.length <= 0){
				hexColor = options.defaultColor;
			}
			_setFromHEX(hexColor);

			$('#gccolor-current-color').css('background-color', '#' + hexColor)
			                           .attr('data-current-color', hexColor)
			                           .on('click', function() {
			                               _setFromHEX($(this).attr('data-current-color'));
			                               changeColor();
			                           });

			$('#gccolor-submit').on('click', function(){
			    closeDialog($(document).data('gccolor').target, options, false);
			});
			
			$('#gccolor-dialog #gccolor-color').bind('dblclick', function() {
			    closeDialog($(document).data('gccolor').target, options, false);
			});
			
			$('#gccolor-dialog').css('top', $(target).offset().top + $(target).outerHeight());
			$('#gccolor-dialog').css('left', $(target).offset().left);
			//$('#gccolor-dialog').show('slide', {direction: 'up'}, 1000);
			$('#gccolor-dialog').show();
			
            $(document).keyup(closeOnEsc);
            $(document).bind('mousedown', closeOnOutsideClick);
		},
		changeColor = function(){
			if (typeof $(document).data('gccolor').options.onChange == 'function'){
				$(document).data('gccolor').options.onChange($(document).data('gccolor').target, _RGBtoHEX(_HSBtoRGB($(document).data('gccolor').hsb)));
			}
		},
		closeDialog = function(target, options, cancel){
			$(document).unbind('keyup', closeOnEsc);
			$(document).unbind('mousedown', closeOnOutsideClick);
			$('#gccolor-dialog #gccolor-color').unbind('dblclick');
			$('#gccolor-current-color').unbind('click');

			if (typeof options.onClose == 'function'){
				options.onClose(target, $('#gccolor-hex input').val(), cancel);
			}

			var color_hex_value = cancel ? $('#gccolor-current-color').attr('data-current-color') : $('#gccolor-hex input').val();

			$(target).val(color_hex_value);
			updateTargetColor($(target));

			$('#gccolor-dialog').hide();
			$('#gccolor-dialog').dialog('destroy');
		},
		
		updateTargetColor = function(target) {
		    var value = $(target).val()
		    $(target).css('background-color', '#' + value);
            changeTextColor(target, value);
		},
		
        changeTextColor = function(target, value) {
            if (_RGBtoHSB(_HEXtoRGB(value)).b > 60) {
                target.css('color', 'black');
            } else {
                target.css('color', 'white');
            }
        };

		return {
			init : function(options){
				options = $.extend({}, defaults, options||{});
				if (_uiInstalled){
					if (!$('#gccolor-dialog').is('div')){
						// We need only one instance
						$('body').append(_dialogBody);
					}
				} else {
					alert('Sorry, jQuery UI plug-in is required for GcColor to work!');
				}

				$('#gccolor-dialog span').bind('mousedown', _startUnit);
				$('#gccolor-hue').bind('mousedown', _startHue);
				$('#gccolor-color > div').bind('mousedown',_startColor);

				return this.each(function() {
					if (options.useButton){
						$(this).wrap('<span class="gccolor-wrapper"></span>')
						$(this).after('<a href="Javascript:;" class="gccolor-button">Pick a color!</a>');
						var button = $(this).next();
						$(this).width($(this).width() - 24);
						$(this).css('margin-right', '24px');
						
						button.css('left', 'auto')
						      .css('right', 0)
						      .css('top', -3);

						//button.css('left', ($(this).position().left + $(this).outerWidth(true) - 22) + 'px');
						button.on('click', function(){
						    toggleDialog($(this).prev(), options);
						});
						updateTargetColor($(this));

                        $(this).bind('gccolor-input-change', function(){
                            updateTargetColor($(this));
                        }).bind('change', function(){
                            $(this).trigger('gccolor-input-change');
                        });

					} else {
						$(this).on('click', function(){
						    toggleDialog($(this), options);
						});
					}
				});
			}
		};
	}();
	$.fn.extend({
		gccolor : gcColor.init
	});
})(jQuery);