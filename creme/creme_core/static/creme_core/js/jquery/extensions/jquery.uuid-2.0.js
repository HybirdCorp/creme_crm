/*
 * jQuery UUID Generator 2.0.0
 *
 * Copyright 2011 Tiago Mikhael Pastorello Freire a.k.a Brazilian Joe
 *
 * Licensed under the MIT license.
 * http://www.opensource.org/licenses/MIT
 *
 * Functionality: 
 * Usage 1: define the default prefix by using an object with the
 * property prefix as a parameter which contains a string value, 
 * and/or determine the uuid generation mode:
 * (sequential|random) {prefix: 'id',mode:'sequential'}
 * Usage 2: call the function jQuery.uuid() with a 
 * string parameter p to be used as a prefix to generate a random uuid;
 * Usage 3: call the function jQuery.uuid() with no parameters 
 * to generate a uuid with the default prefix; defaul prefix: '' (empty string)
 */
(function ($) {
  /*
  Changes uuid generation mode
  */
  $.uidGen = function (opts) {
    var o = opts || false;
    var prefix = $.uidGen._default_prefix;
    if (typeof(o) == 'object') {
      if (typeof(o.mode) == 'string') {
        if (o.mode == 'random') {
          $.uidGen._mode = 'random';
          $.uidGen.gen = jQuery.uidGen._gen2;
        }else{
          $.uidGen._mode = 'sequential';
          $.uidGen.gen = jQuery.uidGen._gen1;
        }
      }
      if (typeof(o.prefix) == 'string') {
        $.uidGen._default_prefix = o.prefix;
        prefix = o.prefix;
      }
    }else if (typeof(o) == 'string') prefix = o;      
    return prefix+$.uidGen.gen();
  };
  
  $.uidGen._default_prefix = '';
  $.uidGen._separator = '-';
  $.uidGen._counter = 0;
  $.uidGen._mode = 'sequential';
  ///*
  //Generate fragment of random numbers
  //*/
  $.uidGen._uuidlet = function () {
    return(((1+Math.random())*0x10000)|0).toString(16).substring(1);
  };
  /*
  Generates sequential uuid
  */
  $.uidGen._gen1 = function () {
      $.uidGen._counter++;
      return $.uidGen._counter;
  };
  /*
  Generates random uuid
  */
  $.uidGen._gen2 = function () {
    return ($.uidGen._uuidlet()
      +$.uidGen._uuidlet()
      +$.uidGen._separator
      +$.uidGen._uuidlet()
      +$.uidGen._separator
      +$.uidGen._uuidlet()
      +$.uidGen._separator
      +$.uidGen._uuidlet()
      +$.uidGen._separator
      +$.uidGen._uuidlet()
      +$.uidGen._uuidlet()
      +$.uidGen._uuidlet()
    );
  };
  $.uidGen.gen = $.uidGen._gen1;
})(jQuery);
