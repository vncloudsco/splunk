define(
    [
        'jquery',
        'underscore',
        'module',
        'backbone',
        'collections/shared/FlashMessages',
        'splunk_monitoring_console/views/table/controls/SimpleDialog',
        'views/shared/FlashMessagesLegacy',
        'splunk.util'
    ],
    function(
        $,
        _,
        module,
        Backbone,
        FlashMessagesCollection,
        SimpleDialog,
        FlashMessagesView,
        util
    ) {
        return SimpleDialog.extend({
            moduleId: module.id,
            initialize: function(options) {
                var defaults = {};
                this.options = _.extend({}, defaults, this.options);
                SimpleDialog.prototype.initialize.apply(this, arguments);
            },
            render: function() {
                this.$(SimpleDialog.FOOTER_SELECTOR).append(SimpleDialog.BUTTON_DONE);
                return this;
            }
        });
    }
);
