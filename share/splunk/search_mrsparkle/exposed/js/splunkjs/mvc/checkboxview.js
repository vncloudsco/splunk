define(function(require, exports, module) {
    var BaseInputView = require("./baseinputview");
    var Checkbox = require('./components/Checkbox');

    /**
     * @constructor
     * @memberOf splunkjs.mvc
     * @name CheckboxView
     * @description The **Checkbox** view displays a checkbox and returns a `Boolean` value indicating whether it is checked.
     * @extends splunkjs.mvc.BaseInputView
     *
     * @param {Object} options
     * @param {String} options.id - The unique ID for this control.
     * @param {String} [options.default] - The default value.
     * @param {Boolean} [options.disabled=false] - Indicates whether to disable the view.
     * @param {String} [options.initialValue] - The initial value of the input.
     * If **default** is specified, it overrides this value.
     * @param {Object} [options.settings] - The properties of the view.
     * @param {Boolean} [options.value] - The Boolean value of the checkbox.
     *
     * @example
     * require([
     *     "splunkjs/mvc/checkboxview",
     *     "splunkjs/mvc/simplexml/ready!"
     * ], function(CheckboxView) {
     *
     *     // Instantiate components
     *     new CheckboxView({
     *         id: "example-checkbox",
     *         default: false,
     *         el: $("#mycheckboxview")
     *     }).render();
     *
     * });
     */
    var CheckboxView = BaseInputView.extend(/** @lends splunkjs.mvc.CheckboxView.prototype */{
        moduleId: module.id,
        className: "splunk-checkbox",

        options: {
            'default': undefined,
            value: undefined,
            disabled: false
        },

        getReactComponent: function() {
            return Checkbox;
        }
    });

    return CheckboxView;
});
