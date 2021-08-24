define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'util/string_utils'
    ],
    function(
        $,
        _,
        module,
        BaseView,
        string_utils
    ){
        /**
         * @constructor
         * @memberOf views
         * @name Tab
         * @extends {views.BaseView}
         * @description Generic view used for creating metric fields
         *
         * @param {Object} options
         * @param {String} options.tab The identifier of the tab
         * @param {Object} options.label The name of the tab
         * @param {Object} options.targetEntity The entity on the model to observe and update on
         * @param {String} options.targetAttribute The attribute on the model to observe and update on
         * @param {bool} options.listenOnInitialize Whether or not to trigger startListening on initialize
         */
        return BaseView.extend( /** @lends views.MetricsField.prototype */ {
            tagName: 'li',
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                if (!this.options.label) {
                    throw new Error("Tab label is required");
                }
                if (this.options.listenOnInitialize) {
                    this.startListening();
                }
            },
            startListening: function() {
                this.listenTo(this.options.targetEntity, 'change:' + this.options.targetAttribute, this.toggleActive);
            },
            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }
                this.render();
                return BaseView.prototype.activate.apply(this, arguments);
            },
            events: {
                'click a': function(e) {
                    var $target = $(e.currentTarget);
                    var data = {};
                    data[this.options.targetAttribute] = $target.attr('data-tab');
                    var type = $target.attr('data-type');
                    if (type) {
                        data['display.general.type'] = type;
                    }
                    this.options.targetEntity.set(data);
                    e.preventDefault();
                }
            },
            toggleActive: function() {
                (this.options.targetEntity.get(this.options.targetAttribute) === this.options.tab) ?
                    this.$el.addClass('active') :
                    this.$el.removeClass('active');
            },
            render: function() {
                this.$el.html(this.compiledTemplate({
                    _: _,
                    tab: this.options.tab,
                    label: this.options.label
                }));
                this.toggleActive();
                return this;
            },
            template:'\
                <a id="<%- tab %>" class="tab-toggle" href="#" data-tab="<%- tab %>" data-type="<%- tab %>">\
                    <%- label %>\
                </a>\
            '
        });
    }
);
