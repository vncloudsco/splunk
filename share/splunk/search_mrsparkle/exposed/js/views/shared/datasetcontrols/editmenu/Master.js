define(
    [
        'jquery',
        'underscore',
        'module',
        'views/Base',
        'views/shared/datasetcontrols/editmenu/Menu'
    ],
    function (
        $,
        _,
        module,
        BaseView,
        EditMenuPopTart
    ) {
        return BaseView.extend({
            moduleId: module.id,

            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);

                var defaults = {
                    button: true,
                    showOpenActions: false,
                    deleteRedirect: false,
                    fetchDelete: false
                };

                _.defaults(this.options, defaults);
            },

            events: {
                'click a.edit': function(e) {
                    e.preventDefault();
                    this.openEdit($(e.currentTarget));
                }
            },

            openEdit: function($target) {
                if (this.children.editMenuPopTart && this.children.editMenuPopTart.shown) {
                    this.children.editMenuPopTart.hide();
                    return;
                }

                $target.addClass('active');

                this.children.editMenuPopTart = new EditMenuPopTart({
                    model: {
                        application: this.model.application,
                        appLocal: this.model.appLocal,
                        dataset: this.model.dataset,
                        searchJob: this.model.searchJob,
                        serverInfo: this.model.serverInfo,
                        state: this.model.state,
                        timeRange: this.model.timeRange,
                        user: this.model.user
                    },
                    collection: {
                        roles: this.collection.roles,
                        times: this.collection.times
                    },
                    showOpenActions: this.options.showOpenActions,
                    showScheduleLink: this.options.showScheduleLink,
                    deleteRedirect: this.options.deleteRedirect,
                    fetchDelete: this.options.fetchDelete,
                    onHiddenRemove: true,
                    ignoreToggleMouseDown: true
                });
                this.children.editMenuPopTart.render().appendTo($('body'));
                this.children.editMenuPopTart.show($target);
                this.children.editMenuPopTart.on('hide', function() {
                    $target.removeClass('active');
                }, this);
            },

            render: function() {
                var canWrite = this.model.dataset.canWrite(this.model.user.canScheduleSearch(), this.model.user.canRTSearch()),
                    canDelete = this.model.dataset.canDelete();

                if (canWrite || this.options.showOpenActions || canDelete) {
                    this.$el.append('<a class="dropdown-toggle edit' + (this.options.button ? " btn" : "") + '" href="#">' + _("Manage").t() +'<span class="caret"></span></a>');
                }

                return this;
            }
        });
    }
);
