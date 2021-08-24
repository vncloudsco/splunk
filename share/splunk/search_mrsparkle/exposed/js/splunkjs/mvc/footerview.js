define(function (require, exports, module) {
    var BaseSplunkView = require("./basesplunkview");
    var console = require("util/console");

    /**
     * This view has been deprecated. It is now a no op
     */
    var FooterView = BaseSplunkView.extend(/** @lends splunkjs.mvc.FooterView.prototype */{
        moduleId: module.id,
        initialize: function() {
            console.warn('footerview has been deprecated and may be removed in a future release.');
        },
        render: function() {
            return this;
        }
    });

    return FooterView;
});
