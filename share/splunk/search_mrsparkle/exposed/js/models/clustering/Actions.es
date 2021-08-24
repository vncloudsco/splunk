import BaseModel from 'models/Base';

export default BaseModel.extend({
    initialize(options) {
        BaseModel.prototype.initialize.call(this, options);
    },
},
    {
        actions: {
            PUSH: 'push',
            CHECK_RESTART: 'check_restart',
            ROLLBACK: 'rollback',
        },
    },
);
