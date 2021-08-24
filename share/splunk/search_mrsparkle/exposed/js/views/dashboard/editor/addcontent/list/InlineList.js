define(
    [
        'module',
        'jquery',
        'underscore',
        'views/dashboard/editor/addcontent/list/BaseList',
        'views/dashboard/editor/addcontent/list/items/InlineItem'
    ],
    function(module,
             $,
             _,
             BaseList,
             InlineItem) {

        return BaseList.extend({
            moduleId: module.id,
            initialize: function(options) {
                BaseList.prototype.initialize.apply(this, arguments);
            },
            _createEntryView: function(entryModel) {
                return new InlineItem({
                    model: {
                        sidebarState: this.model.sidebarState,
                        inline: entryModel
                    }
                });
            },
            _getItemsCount: function() {
                return this.collection.length;
            }
        });
    });
