define([
    'jquery',
    'underscore',
    'backbone',
    './SplunkInputBase',
    'views/shared/controls/TextareaControl'
], function($, _, Backbone, InputBase, TextAreaControl) {

    var SplunkTextAreaElement = Object.create(InputBase, {

        supportedAttributes: {
            value: [InputBase.ATTRIBUTES.required, InputBase.ATTRIBUTES.pattern]
        },

        createdCallback: {
            value: function() {
                InputBase.createdCallback.apply(this, arguments);
            }
        },

        attachedCallback: {
            value: function() {
                InputBase.attachedCallback.apply(this, arguments);

                var $el = $(this);

                this.view = new TextAreaControl({
                    el: this,
                    model: this.model,
                    modelAttribute: 'value',
                    required: this.model.get('required'),
                    pattern: this.model.get('pattern')
                });
                this.view.render();

                $el.addClass('control');
            }
        },

        detachedCallback: {
            value: function() {
                InputBase.detachedCallback.apply(this, arguments);

                if (this.view) {
                    this.view.remove();
                }
            }
        }

    });

    return document.registerElement('splunk-text-area', {prototype: SplunkTextAreaElement});

});