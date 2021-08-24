define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/Base',
    './Menu',
    './SlideNav',
    './Button',
    './AppNav.pcssm'
],
function(
    $,
    _,
    Backbone,
    module,
    BaseView,
    MenuView,
    MenuContentsView,
    ButtonView,
    css
){
    return BaseView.extend({
        moduleId: module.id,
        css: css,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.listenTo(this.model.appNav, 'change:nav', this.debouncedRender);
            this.listenTo(this.model.application, 'change:page', this.setActiveItem);
        },

        /**
         * Determine if given viewName is in list of nav items.
         * @param items navItems.
         * @param viewName Name of current view.
         * @param isActive Current active state of menu item.
         * @returns If viewName exists in items.
         */
        findActiveInMenu: function(items, viewName, isActive) {
            var isMenuActive = isActive || !!_.findWhere(items, {'viewName': viewName});
            var subMenuItems = _.filter(items, function(item) { return item.submenu; });

            // For each submenu, find if viewName matches current viewName and traverse other submenus.
            if (!isMenuActive && subMenuItems.length) {
                var self = this;
                _.each(subMenuItems, function(menuItem) {
                    if (self.findActiveInMenu(menuItem.submenu, viewName, isMenuActive)) {
                        isMenuActive = true;
                    }
                });
            }
            return isMenuActive;
        },

        render: function() {
            var self = this;
            var navData = this.model.appNav.get('nav');
            var currentSection = this.model.application.get('page');
            var isLite = this.model.serverInfo.isLite();

            if(!navData){return this;}

            this.$el.html(this.compiledTemplate({
                css: this.css
            }));

            $.each(navData, function(index, item){
                var itemView;

                if (item.divider) {
                    var className = isLite ? css.dividerLite : css.dividerEnterprise;
                    self.$('[data-role=app-nav-container]').append('<span class="' + className + '" data-role="divider"></span>');
                } else if (item.submenu && item.submenu.length && item.submenu.length > 0) {
                    //create a menu object

                    itemView = new MenuView({
                        contentView: new MenuContentsView({
                            model: {
                                serverInfo: self.model.serverInfo
                            },
                            navData: item
                        }),
                        toggleView: new ButtonView({
                            label: item.label,
                            title: item.label,
                            menu: true,
                            action: 'toggle',
                            active: self.findActiveInMenu(item.submenu, currentSection),
                            appColor: self.options.getAppColor(),
                            isLite: isLite
                        })
                    });
                } else {
                    itemView = new ButtonView({
                        href: item.uri,
                        external: item.external,
                        title: item.label,
                        label: item.label,
                        active: currentSection === item.viewName,
                        preventDefault: false,
                        dataAttributes: {targetView: item.viewName},
                        appColor: self.options.getAppColor(),
                        isLite: isLite
                    });
                }

                itemView && self.$('[data-role=app-nav-container]').append(itemView.render().$el);
            });

            this.setActiveItem.call(this);
            this.model.appNav.trigger('rendered');

            return this;
        },
        template: '\
            <div data-role="app-nav-container" class="<%-css.appNavInner%>"></div>\
        ',
        setActiveItem: function(){
            if(this.model.application.get('page')){
                //really should be figuring out which button is for this and calling set.
                this.$('[data-target-view=' + this.model.application.get('page') + ']').attr('data-active', 'active');
            }
        }
    });
});
