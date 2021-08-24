import $ from 'jquery';
import _ from 'underscore';
import BaseView from 'views/Base';
import BaseModel from 'models/Base';
import UserModel from 'models/services/authentication/User';
import SearchBNFsCollection from 'collections/services/configs/SearchBNFs';
import SearchBarInput from 'views/shared/searchbarinput/Master';
import MenuAdapter from './MenuAdapter';
import css from './Themes.pcssm';

export default BaseView.extend({
    moduleId: module.id,
    /**
     * @param {Object} options {
     *     model: {
     *         inmem: <models.shared.User>
     *     },
     *     collection: {
     *         searchBNFs: <collections.services.configs.SearchBNFs>
     *     }
     */
    initialize(options, ...rest) {
        BaseView.prototype.initialize.call(this, options, ...rest);

        _.defaults(this.model, {
            content: new BaseModel(),
        });

        this.collection.searchBNFs = this.collection.searchBNFs
            || new SearchBNFsCollection();

        if (!this.collection.searchBNFs.length
            && !this.collection.searchBNFs.isFetching()) {
            const dfd = $.Deferred();
            this.collection.searchBNFs.dfd = dfd;
            this.collection.searchBNFs.fetch({
                data: {
                    app: this.model.application.get('app'),
                    owner: this.model.application.get('owner'),
                    count: 0,
                },
                parseSyntax: true,
                success() {
                    dfd.resolve();
                },
                error() {
                    dfd.resolve();
                },
            });
        }

        this.children.themesMenu = new MenuAdapter({
            model: this.model.inmem.entry.content,
            modelAttribute: 'search_syntax_highlighting',
            items: [{
                label: _('Black on White').t(),
                value: UserModel.EDITOR_THEMES.BLACK_WHITE,
            }, {
                label: _('Light Theme').t(),
                value: UserModel.EDITOR_THEMES.DEFAULT,
            }, {
                label: _('Dark Theme').t(),
                value: UserModel.EDITOR_THEMES.DARK,
            }],
        });

        /* eslint max-len: ["error", { "ignoreStrings": true }] */
        this.model.content.set('search', 'sourcetype=access_* status=200 action=purchase | stats count AS "Total Purchased", dc(productId) AS "Total Products", values(productName) AS "Product Names" BY clientip | rename clientip AS "VIP Customer"');

        this.children.searchBarInput = new SearchBarInput({
            model: {
                user: this.model.inmem,
                content: this.model.content,
                application: this.model.application,
            },
            collection: {
                searchBNFs: this.collection.searchBNFs,
            },
            showLineNumbers: false,
            readOnly: true,
            isTabbable: false,
        });
    },

    render() {
        this.$el.html(this.compiledTemplate({
            css,
        }));
        this.$('[data-themes-role=menu]').append(this.children.themesMenu.render().$el);
        this.$('[data-themes-role=preview]').append(this.children.searchBarInput.render().$el);
        this.children.searchBarInput.reformatSearch();
        return this;
    },

    template: `
        <div class="<%- css.content %>">
            <div class="<%- css.theme %>" data-themes-role="menu">
                <h3 class="<%- css.title %>"><%- _(
                    "Search bar theme").t() %></h3>
            </div>
            <div class="<%- css.theme %>" data-themes-role="preview">
                <h3 class="<%- css.title %>"><%- _("Preview").t() %></h3>
            </div>
        </div>
    `,
});
