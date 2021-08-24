define([
    'jquery',
    'underscore',
    'backbone',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/Control',
    'splunk.util',
    'document-register-element'
], function($, _, Backbone, ControlGroup, Control, SplunkUtil) {

    var EmptyControl = Control.extend({});

    var SplunkControlGroup = Object.create(HTMLDivElement.prototype);

    _.extend(SplunkControlGroup, {

        createdCallback: function() {
            var $el = $(this);
            $el.html($.trim($el.html()));
        },

        attachedCallback: function() {
            var $el = $(this);

            // Get the inner html that will be moved under the control group and empty
            if(!this.htmlToRender) {
                this.htmlToRender = $el.html();
                $el.empty();
            }
            // Get the label and layout
            var layout = $(this).attr('layout');
            var label = $(this).attr('label');
            var helpText = $(this).attr('help');
            var controlGroupConfig = {
                el: this,
                controlType: 'Empty',
                controlTypes: {
                    'Empty': EmptyControl
                },
                label: label,
                help: SplunkUtil.escapeHtml(helpText || '')
            };
            if (layout) {
                controlGroupConfig.controlsLayout = layout;
            }
            this.view = new ControlGroup(controlGroupConfig);
            this.view.render();

            $el.addClass('control-group');

            // Add the original html under the controls div
            $el.find('.controls').html(this.htmlToRender);
        },

        detachedCallback: function() {
            if (this.view) {
                this.view.remove();
            }
        }

    });

    return document.registerElement('splunk-control-group', {prototype: SplunkControlGroup});

});
