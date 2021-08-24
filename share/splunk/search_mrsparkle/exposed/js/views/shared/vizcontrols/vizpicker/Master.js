/*
 * A pop-down dialog for picking a visualization.
 */

define([
            'jquery',
            'underscore',
            'module',
            'models/Base',
            'views/Base',
            'helpers/VisualizationRegistry',
            'uri/route',
            './Dialog',
            './VizNormalizer',
            './Master.pcss'
        ],
        function(
            $,
            _,
            module,
            BaseModel,
            BaseView,
            VisualizationRegistry,
            route,
            Dialog,
            VizNormalizer,
            css
        ) {

    return BaseView.extend({

        /**
         * @param {Object} options {
         *     model: {
         *         report: <models.search.Report>,
         *         application: <models.shared.Application>,
         *         intentionsParser: <models.services.search.IntentionsParser>
         *         user: <models.shared.User>
         *     }
         *     vizTypes (required): [events &| statistics &| visualizations]
         *     saveOnApply: <Boolean> whether to save the report when any changes are submitted
         * }
         */

        moduleId: module.id,

        initialize: function() {
            this.reportModel = this.model.report;
            this.reportContentModel = this.reportModel.entry.content;
            this.intentionsParserModel = this.model.intentionsParser;
            this.applicationModel = this.model.application;
            this.userModel = this.model.user;
            this.vizModel = new BaseModel();
            this.vizNormalizer = new VizNormalizer({
                model: {
                    intentionsParser: this.intentionsParserModel,
                    application: this.applicationModel
                },
                vizTypes: this.options.vizTypes
            });
            this._syncSelectedItemFromConfig();
            BaseView.prototype.initialize.call(this, this.options);
            this.activate();
        },

        events: {
            'click .viz-picker': function(e) {
                e.preventDefault();
                var $target = $(e.currentTarget);
                if ($target.hasClass('disabled')) {
                    return;
                }
                this.children.picker = new Dialog({
                    model: {
                        viz: this.vizModel,
                        user: this.userModel,
                        application: this.applicationModel
                    },
                    items: this.vizNormalizer.listAll(),
                    onHiddenRemove: true,
                    warningMsg: this.options.warningMsg,
                    warningLearnMoreLink: this.options.warningLearnMoreLink,
                    defaultThumbnailPath: this._getDefaultThumbnailPath()
                });
                this.children.picker.render().activate().appendTo($('body'));
                this.children.picker.show($target);
                $target.addClass('active');

                this.listenTo(this.children.picker, 'hidden', function() {
                    $target.removeClass('active');
                });
            }
        },

        startListening: function() {
            this.listenTo(this.reportContentModel, 'change', this._syncSelectedItemFromConfig);
            this.listenTo(this.vizNormalizer, 'itemsChange', function() {
                this.trigger('itemsChange');
            });
            this.listenTo(this.vizModel, 'change:id', function(model, newValue) {
                var reportSettings = VisualizationRegistry.getReportSettingsForId(newValue) || {};
                var reportIsChanging = _(reportSettings).any(function(value, key) {
                    return value !== this.reportContentModel.get(key);
                }, this);
                // Avoid the set and save part if there are no actual changes to the report,
                // this insulates us from calling save() in response to external report change.
                if (!_(reportSettings).isEmpty() && reportIsChanging) {
                    this.reportContentModel.set(reportSettings);
                    if (this.options.saveOnApply) {
                        this.reportModel.save();
                    }
                }
                this.render();
            });
            BaseView.prototype.startListening.apply(this, arguments);
        },

        activate: function() {
            if (this.active) {
                return BaseView.prototype.activate.apply(this, arguments);
            }
            BaseView.prototype.activate.apply(this, arguments);
            this._syncSelectedItemFromConfig();
            return this;
        },

        _syncSelectedItemFromConfig: function() {
            var vizConfig = VisualizationRegistry.findVisualizationForConfig(this.reportContentModel.toJSON());
            this.vizModel.set(vizConfig ? this.vizNormalizer.findById(vizConfig.id) : {});
            this.render();
        },

        getItemCount: function() {
            return this.vizNormalizer.listAll().length;
        },

        _getDefaultThumbnailPath: function(){
            return this.vizNormalizer.getThumbnailPath({ appName: 'system'});
        },

        disable: function(){
            this.options.enabled = false;
            this.$('a.popdown-toggle').addClass('disabled');
        },

        enable: function(){
            this.options.enabled = true;
            this.$('a.popdown-toggle').removeClass('disabled');
        },

        tooltip: function(options){
            this.$('a.popdown-toggle').tooltip(options);
        },

        render: function() {
            if (!this.vizModel.get('id')) {
                this.$el.html(_(this.vizNotFoundTemplate).template({}));
                return this;
            }
            this.$el.html(this.compiledTemplate(this.vizModel.toJSON()));
            return this;
        },

        template: '\
            <a class="btn-pill popdown-toggle viz-picker" href="#" data-selected-id="<%- id %>" aria-label="<%- label %>" aria-describedby="select_viz_tpl">\
                <i class="icon-<%- icon %>"/><span class="link-label"><%- label %></span>\
            </a>\
        ',

        vizNotFoundTemplate: '\
            <a class="btn-pill popdown-toggle viz-picker" href="#">\
                <span class="link-label"><%= _("Select...").t() %></span>\
            </a>\
        '
    });

});
