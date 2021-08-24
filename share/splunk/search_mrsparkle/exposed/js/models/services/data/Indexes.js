define(
    [
        'jquery',
        'underscore',
        'models/EAIBase'
    ],
    function(
        $,
        _,
        EAIBaseModel
    ) {
        return EAIBaseModel.extend({
            url: 'data/indexes',
            urlRoot: "data/indexes",
            defaults: {
                datatype: 'event'
            },

            getDataType: function() {
                return this.entry.content.get("datatype") || 'event';
            },

            getBucketPath: function() {
                var selfStorageBucketPath = this.entry.content.get('archiver.selfStorageBucket');
                var selfStorageBucketFolder = this.entry.content.get('archiver.selfStorageBucketFolder');
                if (selfStorageBucketFolder) {
                    selfStorageBucketPath += '/' + selfStorageBucketFolder;
                }
                return selfStorageBucketPath;
            }
        });
    }
);
