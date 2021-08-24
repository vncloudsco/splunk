define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'views/jobmanager/tablecontrols/bulkactions/Master',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/basemanager/SearchableDropdown/Master',
        'views/shared/controls/TextControl',
        'views/shared/CollectionCount',
        'views/shared/DropDownMenu',
        'views/shared/CollectionPaginator',
        'views/shared/delegates/Dock',
        'collections/services/AppLocals',
        'collections/services/authentication/Users',
        'splunk.util'
    ],
    function(
        _,
        $,
        module,
        Base,
        BulkActionsView,
        SyntheticSelectControl,
        SearchableDropdown,
        TextControl,
        CollectionCount,
        DropDownMenu,
        CollectionPaginator,
        Dock,
        AppLocalsCollection,
        UsersCollection,
        splunkUtil
    )
    {
        return Base.extend({
            moduleId: module.id,
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                
                this.children.totalCount = new CollectionCount({
                    countLabel: _('Jobs').t(),
                    collection: this.collection.jobs,
                    tagName: 'span'
                });

                // App filter
                // Fetching will happen when a user enters a search in the app filter.
                this.collection.appsSearch = new AppLocalsCollection();

                this.children.selectAppFilter = new SearchableDropdown({
                    prompt: _('Filter by app').t(),
                    searchPrompt: _('Lookup an app').t(),
                    multiSelect: false,
                    label: _('App: ').t(),
                    model: this.model.state,
                    modelAttribute: 'app',
                    staticOptions: [
                        {
                            label: _('All').t(),    
                            value: ''
                        }
                    ],
                    collection: {
                        // populates dropdown when a user enters a search to filter by app
                        search: this.collection.appsSearch,
                        // populates dropdown for initial listing of apps on page load, or when no filter is applied
                        listing: this.collection.apps
                    },
                    toggleClassName: 'btn-pill'
                });
                
                // Owner filter
                // Fetching will happen when a user enters a search in the owner filter.
                this.collection.usersSearch = new UsersCollection();

                this.children.selectOwnerFilter = new SearchableDropdown({
                    prompt: _('Filter by owner').t(),
                    searchPrompt: _('Lookup an owner').t(),
                    multiSelect: false,
                    label: _('Owner: ').t(),
                    model: this.model.state,
                    modelAttribute: 'owner',
                    staticOptions: [
                        {
                            label: _('All').t(),
                            value: ''
                        }
                    ],
                    collection: {
                        // populates dropdown when a user enters a search to filter by owner
                        search: this.collection.usersSearch,
                        // populates dropdown for initial listing of owners on page load, or when no filter is applied
                        listing: this.collection.users
                    },
                    toggleClassName: 'btn-pill'
                });
                
                // Status Filter
                var statusItems = [ {label:_('All').t(), value:'*'},
                                    {label:_('Queued').t(), value:'queued'},
                                    {label:_('Parsing').t(), value:'parsing'},
                                    {label:_('Running').t(), value:'running'},
                                    {label:_('Backgrounded').t(), value:'background'},
                                    {label:_('Paused').t(), value:'paused'},
                                    {label:_('Finalizing').t(), value:'finalizing'},
                                    {label:_('Done').t(), value:'done'},
                                    {label:_('Finalized').t(), value:'finalized'},
                                    {label:_('Failed').t(), value:'failed'}
                                ];
                
                this.children.selectJobStatusFilter = new SyntheticSelectControl({
                    toggleClassName: 'btn-pill',
                    menuWidth: 'narrow',
                    model: this.model.state,
                    modelAttribute: 'jobStatus',
                    items: statusItems,
                    additionalClassNames: 'status-filter',
                    label: _('Status: ').t()
                });
                
                // Text Filter
                this.children.textFilter = new TextControl({
                    className: 'control name-filter-container',
                    model: this.model.state,
                    modelAttribute: "filter",
                    inputClassName: 'search-query',
                    placeholder: _("filter").t(),
                    canClear: true,
                    updateOnKeyUp: 250
                });
                
                this.children.count = new SyntheticSelectControl({
                    model: this.model.state,
                    modelAttribute: 'countPerPage',
                    items: [
                        { value: '10',  label: _('10 Per Page').t()  },
                        { value: '20',  label: _('20 Per Page').t()  },
                        { value: '50',  label: _('50 Per Page').t()  }
                    ],
                    menuWidth: "narrow",
                    toggleClassName: 'btn-pill',
                    nearestValue: true,
                    additionalClassNames: 'count-per-page'
                });
                
                this.children.bulkAction = new BulkActionsView({
                    model: {
                        application: this.model.application
                    },
                    collection: {
                        selectedJobs: this.collection.selectedJobs
                    }
                });
                
                this.children.collectionPaginator = new CollectionPaginator({
                    collection: this.collection.jobs,
                    model: this.model.state,
                    countAttr: 'countPerPage'
                });
                
                this.activate();
            },
            
            startListening: function() {
                this.listenTo(this.model.state, 'change:app change:owner change:filter change:jobStatus', function() {
                    this.model.state.set('offset', 0);
                });
            },
            
            render: function() {
                if (!this.el.innerHTML) {
                    this.$el.html(this.compiledTemplate());
                    var $filtersContainer = this.$('.filters-container'),
                        $selectedContainer = this.$('.selected-container');
                    this.children.totalCount.render().appendTo($filtersContainer);
                    if (this.model.user.canUseApps()) {
                        this.children.selectAppFilter.render().appendTo($filtersContainer);
                    }
                    this.children.selectOwnerFilter.render().appendTo($filtersContainer);
                    this.children.selectJobStatusFilter.render().appendTo($filtersContainer);
                    this.children.textFilter.render().appendTo($filtersContainer);
                    this.children.count.render().appendTo($filtersContainer);
                    this.children.bulkAction.render().appendTo($selectedContainer);
                    this.children.collectionPaginator.render().appendTo($selectedContainer);

                    this.children.tableDock = new Dock({ el: this.el, affix: '.filters-container, .selected-container' });
                }
                
                return this;
            },

            template: '\
                <div class="filters-container"></div>\
                <div class="selected-container"></div>\
            '
        });
    }
);