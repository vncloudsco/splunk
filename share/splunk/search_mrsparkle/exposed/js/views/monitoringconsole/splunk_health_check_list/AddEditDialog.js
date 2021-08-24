define([
    'jquery',
    'underscore',
    'module',
    'views/monitoringconsole/utils',
    'views/shared/Modal',
    'views/shared/basemanager/EditDialog',
    'views/shared/FlashMessages',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/MultiInputControl',
    'views/shared/controls/SyntheticSelectControl',
    'splunk.util'
], function (
    $,
    _,
    module,
    utils,
    Modal,
    EditDialog,
    FlashMessages,
    ControlGroup,
    MultiInputControl,
    SyntheticSelectControl,
    splunkUtil
) {
    return EditDialog.extend({
        moduleId: module.id,
        setFormControls: function() {
            this.children.flashMessagesView = new FlashMessages({
                model: this.model.entity,
                helperOptions: {
                    removeServerPrefix: true
                }
            });

            this.children.entryFlashMessagesView = new FlashMessages({
                model: this.model.entity.entry,
                helperOptions: {
                    removeServerPrefix: true
                }
            });

            this.children.entryContentFlashMessagesView = new FlashMessages({
                model: this.model.entity.entry.content,
                helperOptions: {
                    removeServerPrefix: true
                }
            });

            this.children.title = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'title',
                    model: this.model.entity.entry.content
                },
                controlClass: 'controls-block',
                label: _('Title').t()
            });

            this.children.name = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'name',
                    model: this.model.entity.entry
                },
                controlClass: 'controls-block',
                label: _('ID').t(),
                help: _('The health check ID can only contain letters, numbers, dashes, and underscores. Do not start the health check ID with a period.').t(),
                // allow edit ID only when it is a new entity or a cloned entity
                enabled: !!(this.model.entity.isNew() || this.options.isClone)
            });

            if (this.model.entity.isNew() || this.options.isClone) {
                this.model.entity.entry.acl.set({'app': this.model.application.get('app')});
            }
            this.appChoice = new SyntheticSelectControl({
                toggleClassName: 'btn',
                model: this.model.entity.entry.acl,
                modelAttribute: 'app'
            });
            var items = [];
            _.each(this.collection.appLocalsUnfilteredAll.models, function(app) {
                if (app.entry.acl.get("can_write") && app.entry.get('name') !== 'launcher') {
                    items.push({
                        label: splunkUtil.sprintf(_('%s (%s)').t(), app.entry.content.get('label'), app.entry.get("name")),
                        value: app.entry.get('name')
                    });
                }
            }, this);
            this.appChoice.setItems(items);

            this.children.app = new ControlGroup({
                controlClass: 'controls-block',
                controls: [this.appChoice],
                label: _('App').t(),
                tooltip: ''
            });

            this.children.category = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'category',
                    model: this.model.entity.entry.content
                },
                controlClass: 'controls-block',
                label: _('Category').t()
            });

            this.children.tags = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'tags',
                    model: this.model.entity.entry.content
                },
                controlClass: 'controls-block',
                label: _('Tags').t()
            });

            this.children.description = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'description',
                    model: this.model.entity.entry.content,
                    placeholder: _('optional').t()
                },
                controlClass: 'controls-block',
                label: _("Description").t()
            });

            this.children.failureText = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'failure_text',
                    model: this.model.entity.entry.content,
                    placeholder: _('optional').t()
                },
                controlClass: 'controls-block',
                label: _("Failure text").t()
            });

            this.children.suggestedAction = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'suggested_action',
                    model: this.model.entity.entry.content,
                    placeholder: _('optional').t()
                },
                controlClass: 'controls-block',
                label: _("Suggested action").t()
            });

            this.children.search = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'search',
                    model: this.model.entity.entry.content
                },
                controlClass: 'controls-block',
                label: _("Search").t()
            });

            if (this.model.dmcConfigs.isDistributedMode()) {
                var applicableGroupsAutoComplete = this.model.dmcConfigs.getDistsearchGroups().map(function(group) {
                    return {
                        text: utils.ROLE_LABELS[group.getDisplayName()] || group.getDisplayName(),
                        id: group.getGroupName()
                    };
                });
                this.applicableGroupsControl = new MultiInputControl({
                    modelAttribute: 'applicable_to_groups',
                    model: this.model.entity.entry.content,
                    autoCompleteFields: applicableGroupsAutoComplete,
                    placeholder: _('optional').t()
                });

                this.children.applicableToGroups = new ControlGroup({
                    controlClass: 'controls-block',
                    controls: [this.applicableGroupsControl],
                    label: _('Applicable to roles').t(),
                    tooltip: _('Leave empty to have this health check apply to all groups.').t()
                });
            }

            var environmentsToExcludeAutoComplete = [
                {text: _('Standalone').t(),
                 id: 'standalone'},
                {text: _('Distributed').t(),
                 id: 'distributed'}
            ];
            this.excludedEnvironmentsControl = new MultiInputControl({
                modelAttribute: 'environments_to_exclude',
                model: this.model.entity.entry.content,
                autoCompleteFields: environmentsToExcludeAutoComplete,
                placeholder: _('optional').t()
            });
            this.children.excludedEnvironments = new ControlGroup({
                controlClass: 'controls-block',
                controls: [this.excludedEnvironmentsControl],
                label: _('Environments to exclude').t(),
                tooltip: _('Leave empty to have this health check apply to all environments.').t()
            });

            this.children.drilldown = new ControlGroup({
                controlType: 'Textarea',
                controlOptions: {
                    modelAttribute: 'drilldown',
                    model: this.model.entity.entry.content,
                    placeholder: _('optional').t()
                },
                controlClass: 'controls-block',
                label: _('Drilldown').t(),
                tooltip: _('Link to a search or Monitoring Console dashboard for additional information.').t()
            });
        },

        renderFormControls: function($form) {
            this.children.flashMessagesView.render().appendTo($form);
            this.children.entryFlashMessagesView.render().appendTo($form);
            this.children.entryContentFlashMessagesView.render().appendTo($form);
            this.children.title.render().appendTo($form);
            this.children.name.render().appendTo($form);
            this.children.app.render().appendTo($form);
            if (!this.model.entity.isNew() && !this.options.isClone) {
                this.children.app.disable();
            }
            this.children.category.render().appendTo($form);
            this.children.tags.render().appendTo($form);
            this.children.description.render().appendTo($form);
            this.children.failureText.render().appendTo($form);
            this.children.suggestedAction.render().appendTo($form);
            this.children.search.render().appendTo($form);
            if (this.model.dmcConfigs.isDistributedMode()) {
                this.children.applicableToGroups.render().appendTo($form);
            }
            this.children.excludedEnvironments.render().appendTo($form);
            this.children.drilldown.render().appendTo($form);
        },

        saveACL: function() {
            // Always save new health checks with global viewing permissions.
            var data = {
                sharing: 'global',
                owner: this.model.user.entry.get('name'),
                'perms.read':'*',
                'perms.write': 'admin'
            };

            return this.model.entity.acl.save({}, {
                data: data,
                success: function(model, response){
                    this.hide();
                    this.model.controller.trigger('refreshEntities');
                }.bind(this)
            });
        }
    });
});
