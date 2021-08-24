define([
    'jquery',
    'underscore',
    'backbone',
    './SplunkInputBase',
    'views/shared/controls/TextControl'
], function($, _, Backbone, InputBase, TextControl) {

    var SplunkTextInputElement = Object.create(InputBase, {

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
                var type = $(this).attr('type');
                // Assume input base has set up the model
                this.view = new TextControl({
                    el: this,
                    model: this.model,
                    modelAttribute: 'value',
                    required: this.model.get('required'),
                    pattern: this.model.get('pattern'),
                    password: type === 'password'
                });
                this.view.render();

                if (type == 'hidden') {
                    this.view.$input.hide();
                }
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

    return document.registerElement('splunk-text-input', {prototype: SplunkTextInputElement});

});
