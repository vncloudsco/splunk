import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Heading from '@splunk/react-ui/Heading';
import P from '@splunk/react-ui/Paragraph';
import PropTypes from 'prop-types';
import Select from '@splunk/react-ui/Select';
import Multiselect from '@splunk/react-ui/Multiselect';
import Text from '@splunk/react-ui/Text';
import Tooltip from '@splunk/react-ui/Tooltip';
import { has } from 'lodash';
import { _ } from '@splunk/ui-utils/i18n';

const Resources = props => (
    <div data-test-name="resources-tabPanel" style={{ minWidth: '353px' }}>
        <Heading data-test-name="resources-tabPanel-heading" level={1}>
            {_('This role')}
        </Heading>
        <ControlGroup
            className="resource-cg"
            data-test-name="default-app-control-group"
            label={_('Default app')}
            labelPosition="top"
        >
            <Select
                filter
                data-test-name="default-app-control"
                value={props.defaultApp}
                onChange={props.handleAppChange}
                style={{ maxWidth: '18em' }}
            >
                {
                    props.apps.map(app => (
                        <Select.Option
                            key={app.value}
                            label={app.value}
                            value={app.value}
                        />))
                }
            </Select>
        </ControlGroup>
        <Heading data-test-name="roleSrchJobLimit-heading">
            {_('Role search job limit')}
        </Heading>
        <P className="resource-help" data-test-name="roleSrchJobLimit-help">
            {_('Set a limit for how many search jobs that all users with this role can run at the same time. ')}
            <Tooltip data-test-name="roleSrchJobLimit-tooltip" content={_('Enter 0 for no search job limits.')} />
        </P>
        <ControlGroup
            className="resource-cg"
            data-test-name="cumulativeSrchJobsQuota-cg"
            label={_('Standard search limit')}
            labelPosition="left"
        >
            <Text
                name="cumulativeSrchJobsQuota"
                className="roles-resourcesInputs"
                data-test-name="cumulativeSrchJobsQuota-text"
                onChange={props.handleResourceChange}
                defaultValue={has(props.resources, 'cumulativeSrchJobsQuota') ?
                    `${props.resources.cumulativeSrchJobsQuota}` : null}
            />
        </ControlGroup>
        <ControlGroup
            className="resource-cg"
            data-test-name="cumulativeRTSrchJobsQuota-cg"
            label={_('Real-time search limit')}
            labelPosition="left"
        >
            <Text
                name="cumulativeRTSrchJobsQuota"
                className="roles-resourcesInputs"
                data-test-name="cumulativeRTSrchJobsQuota-text"
                onChange={props.handleResourceChange}
                defaultValue={has(props.resources, 'cumulativeRTSrchJobsQuota') ?
                    `${props.resources.cumulativeRTSrchJobsQuota}` : null}
            />
        </ControlGroup>
        <Heading data-test-name="userSrchJobLimit-heading">
            {_('User search job limit')}
        </Heading>
        <P className="resource-help" data-test-name="roleSrchJobLimit-help">
            {_('Set a limit for how many search jobs that a single user with this role can run at the same time. ')}
            <Tooltip data-test-name="roleSrchJobLimit-tooltip" content={_('Enter 0 for no search job limits.')} />
        </P>
        <ControlGroup
            className="resource-cg"
            data-test-name="srchJobsQuota-cg"
            label={_('Standard search limit')}
            labelPosition="left"
        >
            <Text
                name="srchJobsQuota"
                className="roles-resourcesInputs"
                data-test-name="srchJobsQuota-text"
                onChange={props.handleResourceChange}
                defaultValue={has(props.resources, 'srchJobsQuota') ?
                    `${props.resources.srchJobsQuota}` : null}
            />
        </ControlGroup>
        <ControlGroup
            className="resource-cg"
            data-test-name="rtSrchJobsQuota-cg"
            label={_('Real-time search limit')}
            labelPosition="left"
        >
            <Text
                name="rtSrchJobsQuota"
                className="roles-resourcesInputs"
                data-test-name="rtSrchJobsQuota-text"
                onChange={props.handleResourceChange}
                defaultValue={has(props.resources, 'rtSrchJobsQuota') ?
                    `${props.resources.rtSrchJobsQuota}` : null}
            />
        </ControlGroup>
        <Heading data-test-name="rst-heading">
            {_('Role search time window limit')}
        </Heading>
        <P className="resource-help" data-test-name="srchTimeWin-help" style={{ maxWidth: '40em' }}>
            {_('Select a time window for searches for this role. Inherited roles can override this setting.')}
        </P>
        <ControlGroup
            data-test-name="restrict-search-time-cg"
            hideLabel
            label={_('Restrict search time range')}
            labelPosition="top"
        >
            <Select
                data-test-name="restrict-search-time-select"
                name="srchTimeWin"
                onChange={props.handleResourceChange}
                style={{ minWidth: '10em' }}
                value={props.resources.srchTimeWin}
            >
                <Select.Option data-test-name="select-opt-unset" label="Unset" value="-1" />
                <Select.Option data-test-name="select-opt-infinite" label="Infinite" value="0" />
                <Select.Option
                    data-test-name="select-opt-custom"
                    label={_('Custom time')}
                    value={(props.resources.srchTimeWin !== '-1' && props.resources.srchTimeWin !== '0')
                        ? props.resources.srchTimeWin : ''}
                />
            </Select>
            { (props.resources.srchTimeWin !== '-1' && props.resources.srchTimeWin !== '0') &&
                (<Text
                    data-test-name="restrict-search-time-text"
                    name="srchTimeWin"
                    onChange={props.handleResourceChange}
                    placeholder="Enter a value in seconds."
                    style={{ maxWidth: '12.5em' }}
                    value={props.resources.srchTimeWin}
                />)
            }
        </ControlGroup>
        <Heading data-test-name="diskSpaceLimit-heading">
            {_('Disk space limit')}
        </Heading>
        <P className="resource-help" data-test-name="roleSrchJobLimit-help">
            {_('Set the maximum amount of disk space, in megabytes, that search jobs for' +
                ' a specific user with this role can use.')}
        </P>
        <ControlGroup
            className="resource-cg"
            data-test-name="srchDiskQuota-cg"
            label={_('Standard search limit')}
            labelPosition="left"
        >
            <Text
                name="srchDiskQuota"
                data-test-name="srchDiskQuota-text"
                onChange={props.handleResourceChange}
                defaultValue={has(props.resources, 'srchDiskQuota') ?
                    `${props.resources.srchDiskQuota}` : null}
                style={{ maxWidth: '8em' }}
            />
            <div style={{ margin: '5px 8px' }}>{_('MB')}</div>
        </ControlGroup>
        {props.shouldShowFederatedProviders
            && [
                <Heading
                    key="federatedProviders-heading"
                    data-test-name="federatedProviders-heading"
                >
                    {_('Federated providers')}
                </Heading>,
                <P className="resource-help" key="federatedProviders-help" data-test-name="federatedProviders-help">
                    {_('Set the federated providers accessible for each user of this role.')}
                </P>,
                <Multiselect
                    name="federatedProviders"
                    key="federatedProviders-select"
                    data-test-name="federatedProviders-select"
                    onChange={props.handleResourceChange}
                    defaultValues={
                        props.resources.federatedProviders ? props.resources.federatedProviders : []
                    }
                    placeholder={_('Select a federated search provider type...')}
                    inline
                    noOptionsMessage={_('You do not have any federated providers available.')}
                >
                    {props.federatedProviders.map(provider => (
                        <Multiselect.Option
                            data-test-name="federatedProviders-select-options"
                            key={provider}
                            label={provider}
                            value={provider}
                        />
                    ))}
                </Multiselect>]}
    </div>
);

Resources.propTypes = {
    apps: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
    })).isRequired,
    handleAppChange: PropTypes.func.isRequired,
    defaultApp: PropTypes.string.isRequired,
    resources: PropTypes.shape({
        federatedProviders: PropTypes.arrayOf(PropTypes.string),
        srchTimeWin: PropTypes.string.isRequired,
        srchJobsQuota: PropTypes.string.isRequired,
        rtSrchJobsQuota: PropTypes.string.isRequired,
        cumulativeSrchJobsQuota: PropTypes.string.isRequired,
        cumulativeRTSrchJobsQuota: PropTypes.string.isRequired,
        srchDiskQuota: PropTypes.string.isRequired,
    }).isRequired,
    shouldShowFederatedProviders: PropTypes.bool.isRequired,
    federatedProviders: PropTypes.arrayOf(PropTypes.string).isRequired,
    handleResourceChange: PropTypes.func.isRequired,
};

export default Resources;
