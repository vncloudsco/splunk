define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'collections/services/data/transforms/MetricSchema',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'views/datapreview/settings/MeasuresField',
        'views/datapreview/settings/BlacklistField',
        'contrib/text!views/datapreview/settings/Metrics.html',
        '../Pane.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        SchemaCollection,
        BaseView,
        ControlGroup,
        MeasuresFieldView,
        BlacklistFieldView,
        metricsTemplate,
        css
    ){
        return BaseView.extend({
            moduleId: module.id,
            className: 'form form-horizontal metrics',
            template: metricsTemplate,
            initialize: function() {

                this.deferreds = {};
                this.setMetricData();

                this.label = _('Presets').t();
                BaseView.prototype.initialize.apply(this, arguments);

                this.children.measuresFieldView = new MeasuresFieldView({
                    model: this.model.metricTransformsModel,
                    name: 'measures',
                    targetAttributeName: 'field_names',
                    heading: _('MEASURES').t(),
                    description: _('Provide at least one measure. Unlisted measures are treated as dimensions.').t(),
                    footer: _('Separate multiple measurements with commas.').t()
                });

                this.children.blacklistFieldView = new BlacklistFieldView({
                    model: this.model.metricTransformsModel,
                    name: 'blacklist',
                    targetAttributeName: 'blacklist_dimensions',
                    heading: _('BLACKLIST').t(),
                    description: _('Provide one or more dimensions that should be omitted from the results.').t(),
                    footer: _('Separate multiple measurements with commas.').t(),
                    placeholderText: _('Optional').t()
                });
            },
            setMetricData: function() {
                var schemaName = this.model.sourcetypeModel.get('ui.metric_transforms.schema_name');
                if (schemaName) {
                    schemaName = schemaName.split('metric-schema:')[1];
                    this.model.metricTransformsModel.set('name', schemaName);
                    this.collection.schema = new SchemaCollection({
                        isCloud: this.model.metricTransformsModel.isCloud,
                        schemaName: schemaName
                    });
                    this.deferreds.schema = this.collection.schema.fetch({});

                    $.when(
                        this.deferreds.schema
                    ).done(function(){
                        this.setMetricFields();
                    }.bind(this));
                }
            },
            setMetricFields: function() {
                var items = this.collection.schema.getAttributes();
                this.model.metricTransformsModel.set(items);
            },
            render: function() {
                this.$el.html(this.compiledTemplate({_:_}));
                this.$('.form-body').append(this.children.measuresFieldView.render().el);
                this.$('.form-body').append(this.children.blacklistFieldView.render().el);
                return this;
            }
        });
    }
);
