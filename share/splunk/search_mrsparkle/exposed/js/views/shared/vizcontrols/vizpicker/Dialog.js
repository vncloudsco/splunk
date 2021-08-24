/*
 * This view provides the popdown dialog for picking a visualization.
 */

define(
    [
        'underscore',
        'jquery',
        'module',
        'models/Base',
        'views/shared/PopTart',
        'uri/route',
        './VizPicker'
    ],
    function(_, $, module, BaseModel, PopTart, route, VizPicker){
        return PopTart.extend({
            moduleId: module.id,
            initialize: function(options) {
                PopTart.prototype.initialize.apply(this, arguments);
                this.children.vizPicker = new VizPicker({
                    model: this.model,
                    items: this.options.items,
                    warningMsg: this.options.warningMsg,
                    warningLearnMoreLink: this.options.warningLearnMoreLink,
                    defaultThumbnailPath: this.options.defaultThumbnailPath
                });
                this.listenTo(this.children.vizPicker, 'vizSelected', function() {
                    this.hide();
                });
            },
            render: function() {
                PopTart.prototype.render.apply(this, arguments);
                var $vizPicker = this.children.vizPicker.render().$el;
                var $selectedItem = $vizPicker.find('.viz-picker-selected-viz-item');
                this.children.vizPicker.appendTo(this.$('.popdown-dialog-body'));
                this.$onOpenFocus = $selectedItem;
                return this;
            },
            template: '\
                <div class="arrow"></div>\
                <div class="popdown-dialog-body"></div>\
            '
        });
    }
);
