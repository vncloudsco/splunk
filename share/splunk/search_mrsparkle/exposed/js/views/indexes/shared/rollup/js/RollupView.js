define([
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/indexes/shared/rollup/js/Sidebar',
        'views/indexes/shared/rollup/js/GeneralPolicy',
        'views/indexes/shared/rollup/js/ExceptionPolicy',
        'views/shared/Tooltip',
        'views/indexes/shared/rollup/RollupView.pcss'
    ],

    function(
        $,
        _,
        module,
        BaseView,
        Sidebar,
        GeneralPolicy,
        ExceptionPolicy,
        Tooltip,
        css
    ) {

        return BaseView.extend({
            moduleId: module.id,
            className: 'rollup-view',
            /**
             * @constructor
             * @memberOf views
             * @name RollupView
             * @extends {views.BaseView}
             * @description View containing all components for metric rollup configuration
             *
             * @param {Object} options
             * @param {Object} options.model The model supplied to this class
             * @param {Object} options.collection The collection supplied to this class
             */
            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                var tabs = this.model.rollup.get('tabs');
                if (tabs && tabs.length) {
                    this.model.rollup.set({ duplicateSummaryError: false });
                    var tabsCopy = $.extend(true, [], this.model.rollup.get('tabs'));
                    tabsCopy[0].listItems = this.collection.dimensions.getItems();
                    this.model.rollup.set('tabs', tabsCopy);
                    this.model.content.set({ tabIndex: '0' });
                } else {
                    this.model.rollup.set({
                        duplicateSummaryError: false,
                        tabs: [
                            {
                                tabBarLabel: _('General Policy').t(),
                                summaries: [],
                                aggregation: 'avg',
                                listType: 'excluded',
                                listItems: this.collection.dimensions.getItems(),
                            }
                        ]
                    });
                    this.model.content.set({
                        tabIndex: '0'
                    });
                }
                this.children.sidebar = new Sidebar({
                    model: {
                        content: this.model.content,
                        rollup: this.model.rollup
                    },
                    collection: {
                        metrics: this.collection.metrics
                    }
                });
                this.children.generalPolicy = new GeneralPolicy({
                    model: {
                        content: this.model.content,
                        rollup: this.model.rollup
                    },
                    collection: {
                        dimensions: this.collection.dimensions,
                        indexes: this.collection.indexes
                    }
                });
                this.startListening();
            },

            startListening: function() {
                this.listenTo(this.model.content, 'change:tabIndex', this.handleTabChange);
                this.listenTo(this.model.rollup, 'change:tabs', function() {
                    if (this.model.content.get('tabIndex') > 0) {
                        this.renderExceptionPolicy();
                    }
                    this.render();
                });
            },

            renderExceptionPolicy: function() {
                if (this.children.exceptionPolicy) {
                    this.children.exceptionPolicy.$el.remove();
                }
                this.children.exceptionPolicy = new ExceptionPolicy({
                    model: {
                        content: this.model.content,
                        rollup: this.model.rollup
                    },
                    collection: {
                        metrics: this.collection.metrics
                    }
                });
                this.children.exceptionPolicy.render().appendTo(this.$(".roll-up-content"));
            },

            handleTabChange: function() {
                var tabIndex = this.model.content.get('tabIndex');
                if (tabIndex > 0) {
                    this.children.generalPolicy.$el.hide();
                    this.renderExceptionPolicy();
                } else {
                    this.children.generalPolicy.$el.show();
                    if (this.children.exceptionPolicy) {
                        this.children.exceptionPolicy.$el.hide();
                    }
                }
            },

            render: function() {
                if (!this.el.innerHTML) {
                    var template = _.template(this.template, {
                        _: _
                    });
                    this.$el.html(template);
                    this.children.generalPolicy.render().appendTo(this.$(".roll-up-content"));
                    this.children.sidebar.render().appendTo(this.$(".roll-up-sidebar-placeholder"));
                }
                return this;
            },

            template: '\
                <span role="group" aria-label="<%- _("Sidebar").t() %>" class="roll-up-sidebar-placeholder"></span>\
                <span class="roll-up-content"></span>\
            '
        });
    });
