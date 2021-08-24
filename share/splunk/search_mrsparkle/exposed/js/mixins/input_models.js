define([
    'jquery',
    'underscore'
], function(
    $,
    _
) {
    return {
        FIELD_PREFIX: 'ui.',

        getPrettyName: function () {
            // cut the http:// prefix from the entity name and return it
            var name = this.entry.get('name');
            if (name.indexOf('http://') === 0) {
                name = name.substring(7);
            }
            return name;
        },

        transposeToRest: function() {
            // clean up all empty values and pick only those starting with prefix
            var newAttrs = {};
            for (var attr in this.attributes) {
                var attrName = attr.substring(this.FIELD_PREFIX.length);
                if (attr.indexOf(this.FIELD_PREFIX) == 0) {
                    var val = this.get(attr);
                    if ((val === null || val === '') && _.isEmpty(this.entry.content.get(attrName))) {
                        continue;
                    } else {
                        if (attr === 'ui.sourcetype' && val === 'default') {
                            // skip default sourcetypes
                            continue;
                        }
                    }
                    newAttrs[attrName] = val;
                }
            }
            this.entry.content.set(newAttrs, {silent: true});
        }
    };
});
