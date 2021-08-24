import { _ } from '@splunk/ui-utils/i18n';
import { find } from 'lodash';
import SearchJob from '@splunk/search-job';
import querystring from 'querystring';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { sprintf } from '@splunk/ui-utils/format';

export const ROLES_COLLECTION_PATH = createRESTURL('authorization/roles');
export const CAPABILITIES_COLLECTION_PATH = createRESTURL('authorization/grantable_capabilities');
export const FEDERATIONS_COLLECTION_PATH = createRESTURL('dfs/federated');
export const MAX_FILTER_LENGTH = 250;
export const DEFAULT_TIMERANGE = '-60s';
export const DEFAULT_TIMERANGE_LABEL = '60 seconds';
export const DEFAULT_CONCAT_OPT = 'OR';
export const WARN_MSG_FIELD_COLLISION = 'The indexed field "%(field)s" that you selected already exists' +
    ' in the SPL search filter. Confirm that the filter has no unintended conflicts in SPL.';
export const WARN_MSG_CONTAINS_EQUALS = 'The SPL search filter contains search terms that use the "="' +
    ' operator. For event data, this type of syntax is not secure, use the "::" operator instead. You' +
    ' can safely use "=" in search terms for metrics data.';


/**
 * Function that returns if source of a capability is native to that role or if it is inherited.
 * @param cap - String. Name of the capability
 * @param role - Object. Current role
 * @returns {String}
 */
export function getCapSource(cap, role) {
    if (role && role.content) {
        if (role.content.imported_capabilities && role.content.imported_capabilities.indexOf(cap) > -1) {
            return _('inherited');
        } else if (role.content.capabilities && role.content.capabilities.indexOf(cap) > -1) {
            return _('native');
        }
        return '';
    }
    return '';
}
/**
 * Create a search job to get all the local and remote indexes.
 * @returns {SearchJob}
 */
export function createSearchJob() {
    return SearchJob.create({
        search: '| eventcount summarize=false index=* index=_* | dedup index | head 1000',
    });
}
/**
 * Function that returns roles with filtered and selected flag to be used under
 * Inheritance tab in the add/edit roles dialog.
 * @param roles - Array of roles fetched from authorization/roles
 * @param currentRole - current role object being created/edited.
 * @returns {[objects]} - Array of roles objects
 */
export function getRolesWithSelection(roles, currentRole) {
    return roles && roles.map(role => ({
        name: role.name,
        filtered: true,
        selected: (currentRole && currentRole.content &&
            currentRole.content.imported_roles.indexOf(role.name) > -1),
        capabilities: (role && role.content && role.content.capabilities && role.content.imported_capabilities &&
            role.content.capabilities.concat(role.content.imported_capabilities)),
    }));
}
/**
 * Function that returns existing providers' names
 * Inheritance tab in the add/edit roles dialog.
 * @param providers - Array of federated providers fetched from dfs/federated
 * @returns {[String]} - Array of string
 */
export function getProvidersName(providers) {
    return providers.map(provider => provider.name);
}
/**
 * Function that finds and sets capabilties that are imported
 * @param roles - Array of role objects
 * @returns {Set} - Set of imported capabilities for all roles that are selected
 */
export function getImportedCaps(roles) {
    // Get all capabilities for roles selected and remove duplicate capabilities
    return roles.reduce((capabilities, role) => {
        if (role.selected) {
            role.capabilities.forEach(cap => capabilities.add(cap));
        }
        return capabilities;
    }, new Set());
}
/*
  * Function parses through array of Capability objects and updates the source and/or
  * selected attributes
  * @param caps - Array of capability objects
  * @param importedCaps - Set of imported capabilities for all roles that are selected
  * @returns Updated array of capability objects
*/
export function updateCaps(caps, importedCaps) {
    const updatedCapsList = caps.map((cap) => {
        const updatedCap = { ...cap };
        updatedCap.isPreview = importedCaps.has(cap.name);
        if (!updatedCap.isPreview && cap.source === 'inherited') {
            // When unselecting an inherited role containing a capability that is also in the
            // active role, we must reset source and selected.
            updatedCap.source = '';
            updatedCap.selected = false;
        }
        return updatedCap;
    });
    return updatedCapsList;
}
/**
 * Function that returns capabilities with ui specific properties to be used under
 * Capabilities tab under add/edit roles dialog.
 * @param {[objects]} caps - Array of capabilities fetched from authorization/capabilities.
 * @param {object} currentRole - current role object being created/edited.
 * @returns {[objects]} - Array of capabilities
 */
export function getCapsWithSelection(caps, currentRole) {
    return caps && caps.map(cap => ({
        name: cap,
        filtered: true,
        source: getCapSource(cap, currentRole),
        selected: (currentRole && currentRole.content &&
            (currentRole.content.imported_capabilities.indexOf(cap) > -1 ||
            currentRole.content.capabilities.indexOf(cap) > -1)) || false,
        isPreview: false,
    }));
}
/**
 * Function that returns indices with ui specific properties to be used under
 * Indexes tab under add/edit roles dialog.
 * @param {[objects]} indexes - Array of capabilities fetched from authorization/capabilities.
 * @param {object} currentRole - current role object being created/edited.
 * @returns {[objects]} - Array of indexes
 */
export function getSelectedIndexes(indexes, currentRole) {
    return indexes && indexes.map((index) => {
        if (index.index === '*' || index.index === '_*') {
            return ({
                name: index.index,
                filtered: true,
                label: index.index === '*' ? _('All non-internal indexes') : _('All internal indexes'),
                imported_srchDefault: (currentRole && currentRole.content
                    && currentRole.content.imported_srchIndexesDefault.indexOf(index.index) > -1),
                imported_srchAllowed: (currentRole && currentRole.content
                    && currentRole.content.imported_srchIndexesAllowed.indexOf(index.index) > -1),
                srchDefault: (currentRole &&
                    currentRole.content && currentRole.content.srchIndexesDefault.indexOf(index.index) > -1),
                srchAllowed: (currentRole &&
                    currentRole.content && currentRole.content.srchIndexesAllowed.indexOf(index.index) > -1),
            });
        }
        return ({
            name: index.index,
            filtered: true,
            imported_srchDefault: (currentRole && currentRole.content
                && currentRole.content.imported_srchIndexesDefault.indexOf(index.index) > -1),
            imported_srchAllowed: (currentRole && currentRole.content
                && currentRole.content.imported_srchIndexesAllowed.indexOf(index.index) > -1),
            srchDefault: (currentRole && currentRole.content &&
                currentRole.content.srchIndexesDefault.indexOf(index.index) > -1),
            srchAllowed: (currentRole && currentRole.content &&
                currentRole.content.srchIndexesAllowed.indexOf(index.index) > -1),
        });
    });
}
/**
 * Function that returns the title of the add/edit roles dialog.
 * @param {String} action - either 'new' or 'edit'
 * @returns {String/null} - returns string with accepted action string. null otherwise.
 */
export function getModalTitle(action) {
    switch (action) {
        case 'new':
            return _('New');
        case 'edit':
            return _('Edit');
        case 'clone':
            return _('Clone');
        default:
            return null;
    }
}
/**
 * Function that returns the label of the primary button on add/edit roles dialog.
 * @param {String} action - either 'new' or 'edit'
 * @param {Boolean} isWorking - Bool to indicate if the create/edit fetch call is in progress.
 * @returns {String}
 */
export function getButtonLabel(isWorking, action) {
    if (isWorking) {
        switch (action) {
            case 'new':
                return _('Creating...');
            default:
                return _('Saving...');
        }
    } else {
        switch (action) {
            case 'new':
                return _('Create');
            default:
                return _('Save');
        }
    }
}
/**
 * Function that returns the data object to POST to the create/edit roles endpoint.
 * @param {object} pData - Initial post data to work with.
 * @param resources - All the properties under the Resources tab in create/edit dialog.
 * @param roles - Selected roles under the Inheritance tab in create/edit dialog.
 * @param selectedCaps - selected capabilities under the Capabilities tab in create/edit dialog.
 * @param indexes - selected default and allowed indices under the Indexes tab in create/edit dialog.
 * @returns {object} - final post data.
 */
export function constructPostData(pData, { resources, roles, selectedCaps, indexes }) {
    const postData = pData;
    Object.keys(resources).forEach((key) => {
        postData[key] = resources[key];
    });
    const importedRoles = roles.filter(role => role.selected);
    const capabilities = selectedCaps.filter(cap => cap.selected && !cap.isPreview && cap.source !== 'inherited');
    const srchIndexesDefault = indexes.filter(index => index.srchDefault);
    const srchIndexesAllowed = indexes.filter(index => index.srchAllowed);
    postData.imported_roles = (importedRoles.length > 0) ? importedRoles.map(role => role.name) : '';
    postData.capabilities = (capabilities.length > 0) ? capabilities.map(cap => cap.name) : '';
    postData.srchIndexesDefault = (srchIndexesDefault.length > 0) ?
        srchIndexesDefault.map(ind => ind.name) : '';
    postData.srchIndexesAllowed = (srchIndexesAllowed.length > 0) ?
        srchIndexesAllowed.map(ind => ind.name) : '';

    const fshSearchCap = find(selectedCaps, cap => cap.name === 'fsh_search');
    if ((fshSearchCap && fshSearchCap.selected)
        || (pData.federatedProviders && resources.federatedProviders.length)) {
        /** with fsh_search capability, all changes related federated providers should be saved
         *  without fsh_search capability, federated providers changes should be saved.
         * Backend will report error to notify user
         */
        postData.federatedProviders = resources.federatedProviders.join(',');
    } else {
        delete postData.federatedProviders;
    }
    return postData;
}
/**
 * Function that returns one of ['none', 'all, 'some'] to represent toggleAll checkbox
 * @param {[objects]} data
 * @returns {String}
 */
export function rowRolesSelectionState(data) {
    if (data) {
        const selectedCount = data.reduce((count, { selected }) => (selected ? count + 1 : count), 0);
        if (selectedCount === 0) {
            return 'none';
        } else if (selectedCount === data.length) {
            return 'all';
        }
        return 'some';
    }
    return 'none';
}
/**
 * Construct the url to call the Delete role endpoint.
 * @param {String} title
 * @returns {String}
 */
export function getDeleteRoleUrl(title) {
    const data = { output_mode: 'json' };
    return createRESTURL(
        `${ROLES_COLLECTION_PATH}/${encodeURIComponent(title)}?${querystring.encode(data)}`);
}
/**
 * Construct the url to call the Capabilities endpoint.
 * @returns {String}
 */
export function getCapabilitiesUrl() {
    const data = { output_mode: 'json' };
    return createRESTURL(
        `${CAPABILITIES_COLLECTION_PATH}?${querystring.encode(data)}`);
}
/**
 * Construct the url to call the Roles endpoint.
 * @returns {String}
 */
export function getRolesUrl() {
    const data = { count: -1, output_mode: 'json' };
    return createRESTURL(
        `${ROLES_COLLECTION_PATH}?${querystring.encode(data)}`);
}
/**
 * Construct the url to call the Federated Providers endpoint.
 * @returns {String}
 */
export function getFederationsUrl() {
    const data = { count: 0, output_mode: 'json' };
    return createRESTURL(`${FEDERATIONS_COLLECTION_PATH}?${querystring.encode(data)}`);
}
/**
 * Function that toggles the row to selected/un-selected.
 * @param {[objects]} data
 * @param {String} name - name of the object to toggle selection
 * @param {string} type - name of the property in the object to toggle.
 * @returns {[objects]}
 */
export function toggleSelected(data, { name, type = null }) {
    const selected = find(data, { name });
    if (selected) {
        if (type) {
            /**
             * Indexes being marked as default should also be marked as selected.
             * Similarly, indexes unchecked as allowed should be unchecked as default."
             */
            if ((type === 'srchDefault' && !selected[type] && !selected.srchAllowed) ||
                (type === 'srchAllowed' && selected[type] && selected.srchDefault)) {
                selected.srchDefault = !selected.srchDefault;
                selected.srchAllowed = !selected.srchAllowed;
            } else {
                selected[type] = !selected[type];
            }
        } else {
            selected.selected = !selected.selected;
        }
    }
    return data;
}
/**
 * Function to toggle all the rows in the table.
 * @param {[objects]} data
 * @returns {[objects]} array of object with the selected property toggled for all rows.
 */
export function toggleAll(data) {
    const state = rowRolesSelectionState(data);
    const selected = state !== 'all';
    const result = data.map(row => ({ ...row, selected }));
    return result;
}
/**
 * Function to filter data based on the name input.
 * @param {[objects]} data - Data structure storing roles, selectedCaps, or indexes
 * @param {String} stateVar - Name of the state variable that stores the data above
 * @param {String} name - Specifies what type of filtering should be done.
 * @param {String} value - Required to filter by name.
 * @returns {[objects]}
 */
export function filterData(data, stateVar, name, value = '') {
    return data && data.map((ind) => {
        const item = { ...ind };
        switch (name) {
            case 'selected':
                if (stateVar === 'roles') {
                    item.filtered = ind.selected;
                } else if (stateVar === 'selectedCaps') {
                    item.filtered = ind.isPreview || ind.selected;
                } else if (stateVar === 'indexes') {
                    item.filtered = ind.srchAllowed || ind.srchDefault || ind.imported_srchAllowed ||
                        ind.imported_srchDefault;
                }
                break;
            case 'unselected':
                if (stateVar === 'roles') {
                    item.filtered = !ind.selected;
                } else if (stateVar === 'selectedCaps') {
                    item.filtered = !ind.isPreview && !ind.selected;
                } else if (stateVar === 'indexes') {
                    item.filtered = !(ind.srchAllowed || ind.srchDefault || ind.imported_srchAllowed ||
                        ind.imported_srchDefault);
                }
                break;
            case 'native':
                if (stateVar === 'selectedCaps') {
                    item.filtered = (ind.source === 'native' || ind.source === '') &&
                    !ind.isPreview && ind.selected;
                } else if (stateVar === 'indexes') {
                    item.filtered = (ind.srchDefault || ind.srchAllowed);
                }
                break;
            case 'inherited':
                if (stateVar === 'selectedCaps') {
                    item.filtered = ind.isPreview || ind.source === 'inherited';
                } else if (stateVar === 'indexes') {
                    item.filtered = ind.imported_srchDefault || ind.imported_srchAllowed;
                }
                break;
            case 'name':
                item.filtered = (ind.name.indexOf(value) !== -1);
                break;
            default:
                item.filtered = true;
        }
        return item;
    });
}
/**
 * Formats state variable generatedSrchFilter that is used to display a preview
 * of the generated search filter in the restrictions tab.
 * @param {String} srchFilter
 * @param {String} concatOpt
 * @param {String} idxFieldSelected
 * @param {String} idxFieldValSelected
 * @returns {String}
 */
export function genSrchFilter(srchFilter, concatOpt, idxFieldSelected, idxFieldValSelected) {
    let srchFilterStr = '';
    // Only include concatOpt if the srchFilter is not empty
    if (srchFilter.trim() !== '') {
        srchFilterStr += ` ${concatOpt} `;
    }
    if (idxFieldSelected && idxFieldValSelected.length === 0) {
        srchFilterStr += `${idxFieldSelected}`;
    }
    if (idxFieldSelected && idxFieldValSelected.length > 0) {
        srchFilterStr += idxFieldValSelected.reduce((acc, val, i) => {
            let fieldValStr = acc;
            fieldValStr += `${idxFieldSelected}::${val}`;
            if (i === idxFieldValSelected.length - 1) {
                fieldValStr += ')';
            } else {
                fieldValStr += ' OR ';
            }
            return fieldValStr;
        }, '(');
    }
    return srchFilterStr;
}

/**
 * Formats the filter menu dropdown to show the active filter option selected
 * @param {String} menuSelected
 * @returns {String}
 */
export function getMenuLabel(menuSelected) {
    // Convert "uninherited" in the indexes tab to "native" to be consistent with the rest of the other tabs
    const menuLabel = `${menuSelected === 'uninherited' ? 'native' : menuSelected}`;
    // Return string with the first character capitalized
    return menuLabel.charAt(0).toUpperCase() + menuLabel.slice(1);
}

/**
 * Runs regex against srchFilter to check if it contains any instance of the '=' operator.
 * The regex only returns true if the '=' follows a word. Returns true if match, else false.
 * @param {String} srchFilter
 * @returns {Boolean}
 */
export function hasEquals(srchFilter) {
    return /(\w+)\s*(?:=)/.test(srchFilter);
}

/**
 * Runs regex against srchFilter to check if it contains the field selected followed by
 * either the '::' or '=' operators. Returns true if match, else false.
 * @param {String} fieldSelected
 * @param {String} srchFilter
 * @returns {Boolean}
 */
export function hasFieldCollision(fieldSelected, srchFilter) {
    if (fieldSelected && srchFilter) {
        const fieldRegex = new RegExp(sprintf('%(field)s\\s*(?:::|=)',
            // "*" is a special char in regex and is also a valid field char. To ensure the,
            // regex works properly, we must dynamically escape all instances of "*" in fieldSelected
            { field: fieldSelected.replace(/[*]/g, '\\$&') }));
        return fieldRegex.test(srchFilter);
    }
    return false;
}

/**
 * Ref callback handler passed to error <Message> component in AddEditRoles Modal.Body
 * @param {Object} React ref
 */
export function scrollToErrMsg(ref) {
    if (ref && ref.scrollIntoView) {
        ref.scrollIntoView(false);
    }
}
