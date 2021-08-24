define(['views/Base', 'util/console'],
    function(BaseView, console){
        return BaseView.extend({
            initialize: function() {
                console.warn('footerview has been deprecated and may be removed in a future release.');
                BaseView.prototype.initialize.apply(this, arguments);
            },
            render: function() {
                return this;
            }
        });
    }
);
