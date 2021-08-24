define(function(require, exports, module) {
    var _ = require('underscore');
    var BaseInputView = require("./baseinputview");
    var TextInput = require('./components/TextInput');

    /**
     * @constructor
     * @memberOf splunkjs.mvc
     * @name TextInputView
     * @description The **TextInput** view displays an editable text box.
     * Does not report changes to the displayed value on a keypress until focus
     * is lost or the user presses Enter.
     * @extends splunkjs.mvc.BaseInputView
     *
     * @param {Object} options
     * @param {String} options.id - The unique ID for this control.
     * @param {String} [options.default] - The value to display on startup.
     * @param {Boolean} [options.disabled=false] - Indicates whether to disable the view.
     * @param {String} [options.initialValue] - The initial value of the input.
     * If **default** is specified, it overrides this value.
     * @param {Object} [options.settings] - The properties of the view.
     * @param {String} [options.type="text"] - The type of text field. To display
     * characters as asterisks (*), set this value to "password".
     * @param {String} [options.value] - The value of the text field.
     *
     * @example
     * require([
     *     "splunkjs/mvc",
     *     "splunkjs/mvc/textinputview",
     *     "splunkjs/mvc/simplexml/ready!"
     * ], function(mvc, TextInputView) {
     *
     *     // Instantiate components
     *     new TextInputView({
     *         id: "example-textinput",
     *         value: mvc.tokenSafe("$myTextValue$"),
     *         default: "type here",
     *         el: $("#mytextinputview")
     *     }).render();
     *
     * });
     */
    var TextInputView = BaseInputView.extend(/** @lends splunkjs.mvc.TextInputView.prototype */{
        moduleId: module.id,
        className: "splunk-textinput",

        options: {
            'default': undefined,
            type: 'text',
            value: undefined,
            disabled: false
        },

        getReactComponent: function() {
            return TextInput;
        },

        getState: function() {
            var baseState = BaseInputView.prototype.getState.apply(this, arguments);

            return _.extend({}, baseState, {
                type: this.settings.get('type')
            });
        },

        // This logic applies what Dashboards expects in order for an input to have a "value" - it is not a generally
        // applicable construct, and should only be used by the Dashboard helpers
        _hasValueForDashboards: function() {
            var value = this.settings.get("value");
            var defaultValue = this.settings.get("default");
            var valueIsDefined = value !== undefined && value !== null && value !== '';
            return valueIsDefined || defaultValue === undefined || value === defaultValue;
        }
    });

    return TextInputView;
});
