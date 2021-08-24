import { createRESTURL } from '@splunk/splunk-utils/url';
import { _ } from '@splunk/ui-utils/i18n';
import moment from '@splunk/moment';
import querystring from 'querystring';
import timeUtils from 'util/time';
import { sprintf } from '@splunk/ui-utils/format';
import { isValidTime } from '@splunk/time-range-utils/time';

export const TOKENS_COLLECTION_PATH = createRESTURL('authorization/tokens');
export const TOKEN_AUTH_PATH = createRESTURL('admin/Token-auth/tokens_auth');
export const SPLUNK_TIME_FORMAT = 'ls z';
export const MAX_AUDIENCE_LENGTH = 256;
export const MAX_NAME_LENGTH = 1024;
export const MAX_FILTER_LENGTH = 250;

/**
 * Construct the url to call the Delete token endpoint.
 * @param {String} tokenOwner
 * @param {String} tokenId
 * @returns {String}
 */
export function getDeleteTokenUrl(tokenOwner, tokenId) {
    const data = { id: tokenId, output_mode: 'json' };
    return createRESTURL(
        `${TOKENS_COLLECTION_PATH}/${encodeURIComponent(tokenOwner)}?${querystring.encode(data)}`);
}

/**
 * Construct the url to call the change status token endpoint.
 * @param {String} tokenOwner
 * @param {String} tokenId
 * @returns {String}
 */
export function getChangeStatusURL(tokenOwner, tokenId, status) {
    const data = { id: tokenId, status, output_mode: 'json' };
    return createRESTURL(
        `${TOKENS_COLLECTION_PATH}/${encodeURIComponent(tokenOwner)}?${querystring.encode(data)}`);
}

/**
 * Construct the url to call the enable/disable tokenAuth endpoint.
 * @param {Boolean} isDisabled
 * @returns {String}
 */
export function getToggleTokenAuthURL(isDisabled, defaultExpiration) {
    const data = { disabled: isDisabled, expiration: defaultExpiration, output_mode: 'json' };
    return createRESTURL(`${TOKEN_AUTH_PATH}?${querystring.encode(data)}`);
}

/**
 * Construct the url to call the tokenAuth endpoint.
 * @returns {String}
 */
export function getTokenAuthSettingsURL() {
    const data = { output_mode: 'json' };
    return createRESTURL(`${TOKEN_AUTH_PATH}?${querystring.encode(data)}`);
}

/**
 * Gets button label for change status modal
 * @param {String} isWorking : state of status modal
 * @param {String} status : enabled || disabled
 * @returns {String}
 */
export function getStatusButtonLabel(isWorking, status) {
    if (isWorking) {
        return status === 'enabled' ? _('Disabling...') : _('Enabling...');
    }
    return status === 'enabled' ? _('Disable') : _('Enable');
}

/**
 * Gets save button label for create modal
 * @param {String} isWorking : state of create modal
 * @returns {String}
 */
export function getPrimaryButtonLabel(isWorking) {
    return isWorking ? _('Creating...') : _('Create');
}

/**
 * Gets save button label for create modal
 * @param {String} tokenReady: state of token creation
 * @returns {String}
 */
export function getDefaultButtonLabel(tokenReady) {
    return tokenReady ? _('Close') : _('Cancel');
}

/**
 * Determine if user is able to perform actions based on capabilities
 * @param {Object} permissions : token capabilities
 * @param {String} tokenOwner
 * @param {String} activeUser : Logged in user
 */
export function canPerformAction(permissions, tokenOwner, activeUser) {
    if (permissions.editAll || permissions.editOwn) {
        return true;
    } else if (permissions.editOwnListAll) {
        return tokenOwner === activeUser;
    }
    return false;
}

/**
 * Set props.permissions object based on the User's capabilities
 * @param {Array} capabilities : List of user's capabilities
 * @returns {Object}
 */
export function getTokenPermissions(capabilities) {
    const permissions = {
        read: true,
        canEdit: capabilities.indexOf('edit_tokens_all') > -1 || capabilities.indexOf('edit_tokens_own') > -1,
        editAll: capabilities.indexOf('edit_tokens_all') > -1,
        editOwnListAll: (capabilities.indexOf('edit_tokens_own') > -1 && capabilities.indexOf('list_tokens_all') > -1),
        editOwn: capabilities.indexOf('edit_tokens_own') > -1 && !(capabilities.indexOf('list_tokens_all') > -1),
        listAll: capabilities.indexOf('list_tokens_all') > -1,
        listOwn: capabilities.indexOf('list_tokens_own') > -1,
        canCreate: capabilities.indexOf('edit_tokens_all') > -1 || capabilities.indexOf('edit_tokens_own') > -1,
        editSettings: capabilities.indexOf('edit_tokens_settings') > -1,
    };
    return permissions;
}

/**
* Converts epoch time to human readable timestamp w/ timezone
* @param {int} epoch
* @returns {String}
*/
export function formatTimestamp(epoch) {
    if (!epoch) {
        return null;
    }
    /**
      moment.getDefaultSplunkTimezone() will return undefined if window.$C.SERVER_ZONEINFO is
      not set (See SPL-165123). splunkMoment.splunkFormat('z') will return the string "undefined"
      when Splunk timezoneOffset is set to system default AND system timezone is set to UTC (See SPL-166348).
      The following "if" block catches these 2 edge cases and will use the standard js Date obj to render
      the timestamp with UTC offset. Otherwise we will render with the timezone string.
    */
    if (!moment.getDefaultSplunkTimezone() ||
        moment.newSplunkTime({ time: epoch * 1000 }).splunkFormat(SPLUNK_TIME_FORMAT).indexOf('undefined') > -1) {
        const dateObj = new Date(epoch * 1000);
        return sprintf(
            _('%(localTimestamp)s %(utcOffset)s UTC'), {
                localTimestamp: timeUtils.convertToLocalTime(epoch),
                utcOffset: timeUtils.getTimezoneString(dateObj),
            },
        );
    }
    return moment.newSplunkTime({ time: epoch * 1000 }).splunkFormat(SPLUNK_TIME_FORMAT);
}

/**
* Format the given epoch seconds to local time. Return Unused if 0
* @param {int} epoch
* @returns {String}
*/
export function formatLastUsedTime(epoch) {
    return epoch === 0 ? _('Unused') : formatTimestamp(epoch);
}

/**
* Format lastUsedIp field. Return Unused if ''
* @param {int} epoch
* @returns {String}
*/
export function formatLastUsedIp(ip) {
    return ip === '' ? _('Unused') : ip;
}

/**
* Format the given epoch seconds to local time. Return Never if 0
* @param {int} epoch
* @returns {String}
*/
export function formatTokenExp(epoch) {
    return epoch === 0 ? _('Never') : formatTimestamp(epoch);
}

/**
 * Check if given name is valid
 * @param {String} name
 * @returns {boolean}
 */
export function isValidName(name) {
    return !!name && name.length < MAX_NAME_LENGTH;
}

/**
 * Check if given audience is valid
 * @param {String} audience
 * @returns {boolean}
 */
export function isValidAudience(audience) {
    return !!audience && audience.length < MAX_AUDIENCE_LENGTH;
}

/**
 * Returns true if user can view tokens, else false
 * @param {Object} permisisons
 * @returns {boolean}
 */
export function canViewTokens(permissions) {
    if (!permissions) {
        return false;
    }
    return !!permissions.editAll || !!permissions.editOwn || !!permissions.listAll
        || !!permissions.listOwn;
}

/**
 * Check if Given time is valid
 * @param {String} time
 * @returns {boolean}
 */
export function isValidTokenTime(time) {
    if (time.charAt(0) === '-' || /^\d+$/.test(time)) {
        return false;
    }
    return isValidTime(time);
}
