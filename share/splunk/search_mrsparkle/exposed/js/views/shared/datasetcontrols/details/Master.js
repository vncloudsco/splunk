define([
        'underscore',
        'jquery',
        'module',
        'models/datasets/PolymorphicDataset',
        'models/datasets/TableAST',
        'views/Base',
        'views/shared/documentcontrols/details/App',
        'views/shared/documentcontrols/details/Permissions',
        'views/shared/documentcontrols/dialogs/permissions_dialog/Master',
        'views/data_model_manager/components/PermissionsDialog',
        'views/shared/documentcontrols/details/ModifiedDate',
        'views/shared/reportcontrols/details/Creator',
        'util/general_utils',
        'splunk.util',
        'uri/route'
    ],
    function(
        _,
        $,
        module,
        PolymorphicDatasetModel,
        TableASTModel,
        BaseView,
        AppView,
        PermissionsView,
        PermissionsDialogView,
        DataModelPermissionsDialog,
        ModifiedView,
        SavedSearchCreatorView,
        generalUtils,
        splunkUtil,
        route
    ) {
        return BaseView.extend({
            moduleId: module.id,
            showLinks: true,

            /**
             * @param {Object} options {
            *       model: {
            *           dataset: <models.Dataset>,
            *           application: <models.Application>,
            *           appLocal: <models.services.AppLocal>,
            *           user: <models.service.admin.user>
            *           serverInfo: <models.services.server.ServerInfo>
            *       },
            *       collection: {
            *          roles: <collections.services.authorization.Roles>,
            *          apps: <collections.services.AppLocals> (Optional for creator view)
            *       },
            *       alternateApp: <alternate_app_to_open>
            * }
            */
            initialize: function(options) {
                var datasetType = this.model.dataset.getType();
                
                BaseView.prototype.initialize.apply(this, arguments);
                
                this.model.tableAST = new TableASTModel();
                
                if (options.showLinks !== undefined) {
                    this.showLinks = generalUtils.normalizeBoolean(options.showLinks);
                }

                this.children.appView = new AppView({ model: this.model.dataset });
                this.children.modifiedView = new ModifiedView({ 
                    model: {
                        document: this.model.dataset
                    } 
                });

                this.children.permissionsView = new PermissionsView({
                    model: {
                        report: this.model.dataset,
                        user: this.model.user,
                        serverInfo: this.model.serverInfo
                    }
                });
            },
            
            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }
                
                var datasetType = this.model.dataset.getType(),
                    currentSearch;
                
                this.tableASTFetchDeferred = $.Deferred();
                
                if (datasetType === PolymorphicDatasetModel.TABLE) {
                    // If we are showing the details of a Table Dataset then we need to check
                    // if the dataset is extended from another dataset.
                    currentSearch = splunkUtil.addLeadingSearchCommand(this.model.dataset.getSearch(), true);
                    
                    // check and see if this is the same search we have already fetched an AST for
                    if ((this.model.tableAST.get('spl') === currentSearch) && this.model.tableAST.get('ast')) {
                        // in this case we don't need to fetch the AST again
                        this.tableASTFetchDeferred.resolve();
                    } else {
                        // ensure the AST is ready to be fetched
                        this.model.tableAST.clear();
                        this.model.tableAST.set({
                            spl: splunkUtil.addLeadingSearchCommand(this.model.dataset.getSearch(), true)
                        });
                        
                        this.tableASTFetchDeferred = this.model.tableAST.fetch({
                            data: {
                                app: this.model.application.get('app'),
                                owner: this.model.application.get('owner')
                            }
                        });
                    }
                    
                } else {
                    this.tableASTFetchDeferred.reject();
                }
                
                return BaseView.prototype.activate.apply(this, arguments);
            },
            
            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }
                
                BaseView.prototype.deactivate.apply(this, arguments);
                this.model.tableAST.fetchAbort();
                
                return this;
            },
            
            events: {
                'click a.edit-permissions': function(e) {
                    var PermissionsDialogConstructor = PermissionsDialogView,
                        // Remember that PolymorphicDatasetModel.DATAMODEL is a Datamodel Dataset. The reason why those aren't acceleratable is that you have to accelerate the
                        // parent Datamodel itself, which means that many Datamodel Datasets in the Datasets Listings page would be accelerated at once.
                        acceleratable = this.model.dataset.typeCanBeAccelerated() && (this.model.dataset.getType() !== PolymorphicDatasetModel.DATAMODEL),
                        originalACL = this.model.dataset.entry.acl.toJSON(),
                        fetchDatasetDeferred = $.Deferred();
                    
                    if (acceleratable) {
                        PermissionsDialogConstructor = DataModelPermissionsDialog;
                        this.model.dataset.fetch({
                            success: function(model, response) {
                                fetchDatasetDeferred.resolve();
                            }.bind(this),
                            error: function(model, response) {
                                fetchDatasetDeferred.resolve();
                            }.bind(this)
                        });
                    } else {
                        fetchDatasetDeferred.resolve();
                    }
                    
                    $.when(fetchDatasetDeferred).then(function() {
                        this.children.permissionsDialog = new PermissionsDialogConstructor({
                            model: {
                                document: this.model.dataset,
                                nameModel: this.model.dataset.entry,
                                user: this.model.user,
                                serverInfo: this.model.serverInfo,
                                application: this.model.application
                            },
                            collection: this.collection.roles,
                            onHiddenRemove: false,
                            nameLabel: this.model.dataset.getDatasetDisplayType()
                        });
                        
                        this.children.permissionsDialog.render().appendTo($("body"));
                        this.children.permissionsDialog.show();
                        
                        if (acceleratable) {
                            this.listenTo(this.model.dataset, 'updateCollection', function() {
                                var currentACL = this.model.dataset.entry.acl.toJSON();
                                
                                // Now, this is going to sound strange, because it is, but we have
                                // to POST the datamodel back to the datamodel endpoint after changing the ACL
                                // to ensure that the conf entry is in the correct state, regardless of what any GET
                                // after the ACL POST tells us.
                                if (!_.isEqual(currentACL, originalACL) && (currentACL.sharing === 'user')) {
                                    this.model.dataset.entry.content.acceleration.set('enabled', 0);
                                    this.model.dataset.save({}, {
                                        success: function(model, response) {
                                            this.model.dataset.entry.content.set('accelerated', false);
                                            if (this.model.state) {
                                                this.model.state.trigger('change:search');
                                            }
                                        }.bind(this)
                                    });
                                }
                                
                                this.stopListening(this.model.dataset, 'updateCollection');
                            }.bind(this));
                        }
                    }.bind(this));
                    
                    e.preventDefault();
                }
            },
            
            render: function() {
                var canWrite = this.model.dataset.canWrite();

                this.el.innerHTML = this.compiledTemplate({
                    _: _,
                    fields: this.model.dataset.getRenderableFieldsList({
                        numFieldsToShow: this.options.numFieldsToShow,
                        showTotal: this.options.showTotal
                    }),
                    canShowCreator: this.canShowCreator,
                    type: this.model.dataset.getDatasetDisplayType()
                });

                if (this.canShowCreator) {
                    this.children.creatorView.render().appendTo(this.$('dd.creator'));
                }

                this.children.appView.render().appendTo(this.$('dd.app'));
                this.children.permissionsView.render().appendTo(this.$('dd.permissions'));
                this.children.modifiedView.render().appendTo(this.$('dd.modified'));

                if (this.showLinks && canWrite && this.model.dataset.canEditPermissions()) {
                    // Only show if user has perm to change perms
                    if (this.model.dataset.entry.acl.get('can_change_perms')) {
                        this.$('dd.permissions').append(_.template(this.permissionsTemplate));
                    }
                }
                
                $.when(this.tableASTFetchDeferred).then(function() {
                    var datasetPayloads = this.model.tableAST.getFromCommandObjectPayloads(),
                        extendedNames = [],
                        currentModel,
                        datasetLink;
                    
                    if (datasetPayloads && datasetPayloads.length) {
                        this.$('.list-dotted').append(_.template(this.extendsTemplate));
                        
                        // TODO: figure out how to show the type of each dataset that has been extended
                        _.each(datasetPayloads, function(datasetPayload) {
                            if (datasetPayload.eai) {
                                currentModel = new PolymorphicDatasetModel(datasetPayload.eai, { parse: true });
                                datasetLink = route.dataset(
                                    this.model.application.get('root'),
                                    this.model.application.get('locale'),
                                    this.model.application.get('app'),
                                    { data: currentModel.getRoutingData() }
                                );

                                extendedNames.push('<a class="extended-link" href="' + datasetLink + '">' + currentModel.getFormattedName() + '</a>');
                            } else {
                                extendedNames.push(datasetPayload.dataset);
                            }
                            
                        }.bind(this));
                        
                        this.$('.extended-datasets').html(extendedNames.join(' > '));
                    }
                
                }.bind(this));
                
                return this;
            },

            template: '\
                <dl class="list-dotted">\
                    <dt class="type"><%- _("Dataset type").t() %></dt>\
                        <dd class="type"><%- type %></dd>\
                    <% if (canShowCreator) { %>\
                        <dt class="creator"><%- _("Creator").t() %></dt>\
                            <dd class="creator"></dd>\
                    <% } %>\
                    <dt class="app"><%- _("App").t() %></dt>\
                        <dd class="app"></dd>\
                    <dt class="permissions"><%- _("Permissions").t() %></dt>\
                        <dd class="permissions"></dd>\
                    <dt class="modified"><%- _("Modified").t() %></dt>\
                        <dd class="modified"></dd>\
                    <dt class="fields"><%- _("Fields").t() %></dt>\
                        <dd class="fields"><%- fields %></dd>\
                </dl>\
            ',
            
            permissionsTemplate: '\
                <a class="edit-permissions" href="#"><%- _("Edit").t() %></a>\
            ',
            
            extendsTemplate: '\
                <dt class="extends"><%- _("Extends").t() %></dt>\
                    <dd class="extended-datasets"></dd>\
            '
        });
    }
);
