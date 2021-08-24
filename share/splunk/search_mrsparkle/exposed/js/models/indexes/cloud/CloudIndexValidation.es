/**
 * Cloud index client side validations - shared accross single instance and clustered environments
 */
import _ from 'underscore';

export const validationObj = { // eslint-disable-line import/prefer-default-export
    name: [{
        fn(value, attr, computedState) {
            if (computedState.isNew) {
                if (_.isUndefined(value)) {
                    return _('Index Name is required.').t();
                }
            }
            return '';
        },
    }, {
        fn(value, attr, computedState) {
            if (computedState.isNew) {
                if (!/^[a-z0-9]([a-z0-9_\-]*)$/.test(value)) { // eslint-disable-line no-useless-escape
                    return _(`Index Names may contain only lowercase letters, numbers, underscores, or hyphens.
                        They must begin with a lowercase letter or number.`).t();
                }
            }
            return '';
        },
    }],
    maxIndexSize: [{
        required: true,
        msg: _('Max Data Size is required.').t(),
    }, {
        pattern: /^[\d]+$/,
        msg: _('Max Data Size must be a positive integer.').t(),
    }, {
        fn(value, attr, computedState) {
            const maxMBSize = 4294967296;
            let inputVal;

            switch (computedState.maxIndexSizeFormat) {
                case 'GB':
                    inputVal = value * 1024;
                    break;
                case 'TB':
                    inputVal = value * 1024 * 1024;
                    break;
                default:
                    inputVal = value;
            }

            if (inputVal >= maxMBSize) {
                return _('Max Data Size is 4194304 GB').t();
            }
            return '';
        },
    }],
    frozenTimePeriodInDays: [{
        required: true,
        msg: _('Retention (days) is required.').t(),
    }, {
        pattern: /^[\d]+$/,
        msg: _('Retention (days) must be a positive integer.').t(),
    }, {
        fn(value, attr, computedState) { // eslint-disable-line no-unused-vars
            if (value > 36500) {
                return _('Max Retention (days) is 36500').t();
            }
            return '';
        },
    }],
};