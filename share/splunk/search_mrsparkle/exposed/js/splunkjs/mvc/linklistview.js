define(function(require, exports, module) {
    var BaseChoiceView = require("./basechoiceview");
    var LinkList = require('./components/LinkList');

    /**
     * Displays a list of links.
     * the value of this control is the value of the single link
     * selected, or undefined if no link is selected.
     */

    /**
     * @constructor
     * @memberOf splunkjs.mvc
     * @name LinkListView
     * @description The **LinkList** view displays a horizontal list with a set
     * of choices. The list can be bound to a search manager, but can also be
     * used as a clickable list that emits change events.
     * @extends splunkjs.mvc.BaseChoiceView
     *
     * @param {Object} options
     * @param {String} options.id - The unique ID for this control.
     * @param {Object[]} [options.choices=[ ]] -  A static dictionary of options for the
     * link list. If bound to a `managerid`, the static choices specified here
     * prepended to the dynamic choices from the search.</br>
     * For example:
     *
     *     var mychoices = [
     *         {label:"text1", value: "value1"},
     *         {label:"text2", value: "value2"},
     *         {label:"text3", value: "value3"}
     *     ];
     *
     * @param {String} [options.default] - The default choice.
     * @param {Boolean} [options.disabled=false] - Indicates whether to disable the view.
     * @param {String} [options.initialValue] - The initial value of the input.
     * If **default** is specified, it overrides this value.
     * @param {String} [options.labelField] -  The UI label to display for each choice.
     * @param {String} [options.managerid=null] - The ID of the search manager to bind
     * this control to.
     * @param {Boolean} [options.selectFirstChoice=false] - Indicates whether to use the
     * first available choice when the user has not made a selection. If the
     * **default** property has been set, that value is used instead.
     * @param {Object} [options.settings] - The properties of the view.
     * @param {String} [options.value] - The value of the current choice.
     * @param {String} [options.valueField] -  The value or search field for each choice.
     *
     * @example
     * require([
     *     "splunkjs/mvc",
     *     "splunkjs/mvc/searchmanager",
     *     "splunkjs/mvc/linklistview",
     *     "splunkjs/mvc/simplexml/ready!"
     * ], function(
     *     mvc,
     *     SearchManager,
     *     LinkListView
     * ) {
     *
     *     // Use this search to populate the link list with index names
     *     new SearchManager({
     *         id: "example-search",
     *         search: "| eventcount summarize=false index=* index=_* | dedup index | fields index",
     *     });
     *
     *     var myLinkListView = new LinkListView ({
     *         id: "linklist1",
     *         selectFirstChoice: false,
     *         searchWhenChanged: true,
     *         managerid: "example-search",
     *         value: mvc.tokenSafe("$mychoice$"),
     *         default: "main",
     *         labelField: "index",
     *         valueField: "index",
     *         el: $("#mylinklist")
     *     }).render();
     *
     *     // Fired when the list value changes
     *     myLinkListView.on("change", function(e) {
     *         // Displays the value of the list in the console
     *         console.log(myLinkListView.settings.get("value"));
     *     });
     *
     * });
     */
    return BaseChoiceView.extend({
        moduleId: module.id,
        className: "splunk-linklist splunk-choice-input",

        options: {
            valueField: '',
            labelField: '',
            'default': undefined,
            choices: [],
            selectFirstChoice: false,
            disabled: false,
            value: undefined
        },

        getReactComponent: function() {
            return LinkList;
        }
    });
});
