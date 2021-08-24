/**
 * Created by ykou on 11/6/15.
 */
define([
    'underscore',
    'views/shared/PopTart'
], function(
    _,
    PopTart
) {
    return PopTart.extend({
        initialize: function() {
            PopTart.prototype.initialize.apply(this, arguments);

            this.listenTo(this.model, 'change', this.render);
        },
        render: function() {
            var $detailContent;

            var detail = this.model.get('detail');

            if (_.isArray(detail)) {
                $detailContent = _.reduce(detail, function(acc, row) {
                    return acc + '<div>' + row + '</div>';
                }, '');
            }
            else {
                $detailContent = detail;
            }

            this.$el.html(this.compiledTemplate({
                detail: $detailContent
            }));
            return this;
        },
        template:
            '<div class="arrow"></div>\
             <div class="dmc-kpi-item-tooltip"><%= detail %></div>'
    });
});