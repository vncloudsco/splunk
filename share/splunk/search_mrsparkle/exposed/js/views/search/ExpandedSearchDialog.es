import _ from 'underscore';
import $ from 'jquery';
import Backbone from 'backbone';
import UserModel from 'models/services/authentication/User';
import Modal from 'views/shared/Modal';
import SearchInputView from 'views/shared/searchbarinput/Master';
import route from 'uri/route';

export default Modal.extend({
    moduleId: module.id,
    className: `${Modal.CLASS_NAME} ${Modal.CLASS_MODAL_WIDE} expanded-search-dialog`,
    /**
     * @param {Object} options {
     *     model: {
     *         user: <models.services.authentication.User> To determine useSyntaxHighlighting
     *              and other search IDE preferences.
     *         application: <models.Application> A model required for searchinput and for route.
     *     },
     *     collection: {
     *         searchBNFs: <collections/services/configs/SearchBNFs> A collection required for searchinput
     *     },
     *     earliest_time (Optional) : <String> For setting the timerange in the search page. Defaults to ''.
     *     latest_time (Optional) : <String> For setting the timerange in the search page. Defaults to ''.
     *     fullSearch (Optional) : <String> Macro and saved search expanded search string. Defaults to ''.
     *     minSearchBarLines (Optional): <Number> minimum lines for the search input. Defaults to 1.
     *     maxSearchBarLines (Optional): <Number> maximum lines for the search input. Defaults to 12.
     * }
     */
    initialize(options, ...rest) {
        Modal.prototype.initialize.call(this, options, ...rest);

        const defaults = {
            fullSearch: '',
            minSearchBarLines: 1,
            maxSearchBarLines: 12,
        };
        this.options = $.extend(true, {}, defaults, this.options);
        this.model.contentModel = new Backbone.Model();
        this.model.contentModel.set('search', this.options.fullSearch);
        this.children.searchInput = new SearchInputView({
            model: {
                user: this.model.user,
                content: this.model.contentModel,
                application: this.model.application,
            },
            collection: {
                searchBNFs: this.collection.searchBNFs,
            },
            minSearchBarLines: this.options.minSearchBarLines,
            maxSearchBarLines: this.options.maxSearchBarLines,
            // search assistant is not needed since searchinput is disabled
            searchAssistant: UserModel.SEARCH_ASSISTANT.NONE,
            readOnly: true,
        });
    },
    events: $.extend({}, Modal.prototype.events, {
        'click a.modal-btn-primary.search-expansion-primary': function onClick(e) {
            e.preventDefault();
            this.hide();
            this.openExpandedSearchStringPage();
        },
    }),
    /**
     * Opens search page in a new tab with macros and saved searches
     * expanded search string.
     */
    openExpandedSearchStringPage() {
        const routeString = route.search(
            this.model.application.get('root'),
            this.model.application.get('locale'),
            this.model.application.get('app'),
            { data: $.extend({}, {
                earliest: this.options.earliest_time,
                latest: this.options.latest_time,
                q: this.children.searchInput.getText(),
            }) });
        window.open(routeString, '_blank');
    },

    render() {
        this.$el.html(Modal.TEMPLATE);
        this.$(Modal.HEADER_TITLE_SELECTOR).html(_('Expanded Search String').t());
        this.children.searchInput.render().appendTo(this.$(Modal.BODY_SELECTOR));
        this.children.searchInput.reformatSearch();
        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
        this.$(Modal.FOOTER_SELECTOR).append(`
            <a href="#" class="search-expansion-primary btn btn-primary modal-btn-primary pull-right">
                ${_('Open as new search').t()}
            </a>`);
        return this;
    },
});