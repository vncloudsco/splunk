/**
 * Created by claral on 9/01/16.
 */
define(
[
    'jquery',
    'underscore',
    'module',
    'backbone',
    'views/Base',
    'views/monitoringconsole/utils',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/MultiInputControl',
    'views/shared/controls/SyntheticSelectControl',
    'views/monitoringconsole/splunk_health_check/Scope.pcss',
    'splunk.util',
    'uri/route'
], function(
    $,
    _,
    module,
    Backbone,
    BaseView,
    utils,
    ControlGroup,
    MultiInputControl,
    SyntheticSelectControl,
    css,
    splunkUtil,
    route
) {
    return BaseView.extend({
        moduleId: module.id,
        className: 'scope',

        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.isMcCloud = this.model.application.get('app') === 'splunk_instance_monitoring';

            if (!this.isMcCloud) {
                this.children.groupFilter = this.prepareGroupView();
            }

            this.children.appFilter = new SyntheticSelectControl({
                label:_('App:').t(),
                toggleClassName: 'btn',
                model: this.model.conductor,
                modelAttribute: 'app'
            });

            var items = [{label: _('All').t(), value: '*'}, {label:_('System default').t(), value: 'system'}];
            _.each(this.collection.appLocalsUnfilteredAll.models, function(app) {
                items.push({
                    label: splunkUtil.sprintf(_('%s (%s)').t(), app.entry.content.get('label'), app.entry.get('name')),
                    value: app.entry.get('name')
                });
            }, this);

            this.children.appFilter.setItems(items);


            var tagsAutoComplete = this.collection.tasks.getTags().map(function(tag) {
                return {
                    text: tag,
                    id: tag
                };
            });
            this.tagsControl = new MultiInputControl({
                modelAttribute: 'tag',
                model: this.model.conductor,
                autoCompleteFields: tagsAutoComplete
            });
            this.children.tagFilter = new ControlGroup({
                controlClass: 'controls-block',
                controls: [this.tagsControl],
                label: _('Tags:').t(),
                tooltip: _('Leave empty to select all tags').t()
            });

            this.children.tagDisplay = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'tag',
                    model: this.model.conductor
                },
                controlClass: 'controls-block',
                label: _('Tags:').t(),
                tooltip: _('Leave empty to select all tags').t(),
                enabled: false
            });

            var categoriesAutoComplete = this.collection.tasks.getCategories().map(function(category) {
                return {
                    text: category,
                    id: category
                };
            });
            this.categoriesControl = new MultiInputControl({
                modelAttribute: 'category',
                model: this.model.conductor,
                autoCompleteFields: categoriesAutoComplete
            });
            this.children.categoryFilter = new ControlGroup({
                controlClass: 'controls-block',
                controls: [this.categoriesControl],
                label: _('Category:').t(),
                tooltip: _('Leave empty to select all categories').t()
            });

            this.children.categoryDisplay = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'category',
                    model: this.model.conductor
                },
                controlClass: 'controls-block',
                label: _('Category:').t(),
                tooltip: _('Leave empty to select all categories').t(),
                enabled: false
            });
        },

        enable: function() {
            if (this.model.dmcConfigs.isDistributedMode() && !this.isMcCloud) {
                this.children.groupFilter.enable();
            }
            this.children.appFilter.enable();
            this.children.tagFilter.show();
            this.children.categoryFilter.show();
            this.children.tagDisplay.hide();
            this.children.categoryDisplay.hide();
        },

        disable: function() {
            if (this.model.dmcConfigs.isDistributedMode() && !this.isMcCloud) {
                this.children.groupFilter.disable();
            }
            this.children.appFilter.disable();
            this.children.tagFilter.hide();
            this.children.categoryFilter.hide();
            this.children.tagDisplay.show();
            this.children.categoryDisplay.show();
        },

        render: function() {

            this.$el.html(this.compiledTemplate());

            this.$('.scope-group').prepend(this.children.appFilter.render().$el);
            if (!this.isMcCloud) {
                this.$('.scope-group').prepend(this.children.groupFilter.render().$el);
            }
            this.$('.scope-filter').append(this.children.tagFilter.render().$el);
            this.$('.scope-filter').append(this.children.categoryFilter.render().$el);

            this.$('.scope-filter').append(this.children.tagDisplay.render().$el);
            this.$('.scope-filter').append(this.children.categoryDisplay.render().$el);
            this.children.tagDisplay.hide();
            this.children.categoryDisplay.hide();

            return this;
        },

        prepareGroupView: function() {
            var isDistributedMode = this.model.dmcConfigs.isDistributedMode();
            if (!isDistributedMode) {
                // single instance mode
                var singleView = new Backbone.View();
                singleView.$el = '<div class="standalone-instance">' + _('Instance: ').t() + this.model.dmcConfigs.getLocalInstanceName() + '</div>';
                return singleView;
            }
            else {
                var groupDropdown = new SyntheticSelectControl({
                    label:_('Group:').t(),
                    toggleClassName: 'btn',
                    model: this.model.conductor,
                    modelAttribute: 'group'
                });

                var items = [{label: _('All').t(), value: '*'}];

                var indexerClustersInnerItems = null;
                var searchHeadClustersInnerItems = null;

                _.each(this.model.dmcConfigs.getDistsearchGroups(), function(group) {
                    if (group.isIndexerClusterGroup()) {
                        if (indexerClustersInnerItems == null) {
                            indexerClustersInnerItems = [{ label:  _('Indexer Clusters').t() }];
                        }
                        indexerClustersInnerItems.push({
                            value: group.getGroupName(),
                            label: utils.ROLE_LABELS[group.getDisplayName()] || group.getDisplayName()
                        });
                    } else if (group.isSearchHeadClusterGroup()) {
                        if (searchHeadClustersInnerItems == null) {
                            searchHeadClustersInnerItems = [{ label:  _('Search Head Clusters').t() }];
                        }
                        searchHeadClustersInnerItems.push({
                            value: group.getGroupName(),
                            label: utils.ROLE_LABELS[group.getDisplayName()] || group.getDisplayName()
                        });
                    } else {
                        items.push([{ label: utils.ROLE_LABELS[group.getDisplayName()] || group.getDisplayName(), value: group.getGroupName()}]);
                    }
                }, this);

                if (indexerClustersInnerItems != null) {items.push(indexerClustersInnerItems);}
                if (searchHeadClustersInnerItems!= null) {items.push(searchHeadClustersInnerItems);}

                groupDropdown.setItems(items);

                return groupDropdown;
            }
        },

        template: '\
            <div class="scope-group">\
                <div class="scope-filter"></div>\
            </div>\
        '
    });
});