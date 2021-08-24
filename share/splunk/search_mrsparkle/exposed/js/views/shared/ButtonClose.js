/* REUSE WITH CAUTION
/* ----------------------------------------------------------
/* This a CSS Module based view should be considered as Beta.
/* API is likely to change       */

define([
    'underscore',
    'module',
    'views/shared/Button',
    './Button.pcssm',
    './ButtonClose.pcssm'
], function(
    _,
    module,
    ButtonView,
    cssButton,
    css
){
    return ButtonView.extend({
        moduleId: module.id,
        constructor: function(options){
            _.extend(this.css, cssButton, css);

            ButtonView.apply(this, arguments);
        },
        initialize: function(options){
            var defaults = {
              style:     'pill',
              action:    'close',
              title:     'close',
              icon:      'close'
            };

            _.defaults(this.options, defaults);

            ButtonView.prototype.initialize.apply(this, arguments);
        }
    });
});
