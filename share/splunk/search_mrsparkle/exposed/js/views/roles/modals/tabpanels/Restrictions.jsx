import React from 'react';
import Button from '@splunk/react-ui/Button';
import ColumnLayout from '@splunk/react-ui/ColumnLayout';
import ComboBox from '@splunk/react-ui/ComboBox';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import Message from '@splunk/react-ui/Message';
import Multiselect from '@splunk/react-ui/Multiselect';
import P from '@splunk/react-ui/Paragraph';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import List from '@splunk/react-ui/List';
import PropTypes from 'prop-types';
import Select from '@splunk/react-ui/Select';
import Text from '@splunk/react-ui/Text';
import 'views/roles/Roles.pcss';
import { _ } from '@splunk/ui-utils/i18n';
import { sprintf } from '@splunk/ui-utils/format';
import { has } from 'lodash';
import { DEFAULT_TIMERANGE, DEFAULT_TIMERANGE_LABEL, WARN_MSG_CONTAINS_EQUALS, WARN_MSG_FIELD_COLLISION,
    hasEquals, hasFieldCollision } from '../../Utils';

const Restrictions = (props) => {
    const equalsWarn = hasEquals(props.srchFilter);
    const fieldCollisionWarn = hasFieldCollision(props.idxFieldSelected, props.srchFilter);
    return (
        <ColumnLayout data-test-name="restrictions-colLay" style={{ minWidth: '353px' }}>
            <ColumnLayout.Row data-test-name="restrictions-heading-row" style={{ marginBottom: '0px' }}>
                <ColumnLayout.Column
                    date-test-name="restrictions-heading-col"
                    span={12}
                    style={{ padding: 10, minHeight: 80 }}
                >
                    <Heading data-test-name="restrictions-heading" level={1}>{_('Restrict searches')}</Heading>
                    <P data-test-name="restrictions-heading-p">
                        {_('Create a search filter to set search restrictions for this role. ' +
                          'You can enter a valid search filter or use the search filter generator to add queries.')}
                    </P>
                </ColumnLayout.Column>
            </ColumnLayout.Row>
            <ColumnLayout.Row
                data-test-name="restrictions-warnings-row"
                style={{ marginBottom: '0px', maxWidth: '1200px' }}
            >
                <ColumnLayout.Column
                    date-test-name="restrictions-warnings-col"
                    span={12}
                    style={{ padding: 10, marginTop: '-35px' }}
                >
                    {props.disableGenerator && (
                        <Message
                            className="restrctionsMsg"
                            data-test-name="restrictions-msg-warn"
                            fill
                            type="warning"
                        >
                            {_('Select at least one index in the Indexes tab to enable the ' +
                              'search filter generator.')}
                        </Message>)
                    }
                    {equalsWarn && (
                        <Message
                            className="restrctionsMsg"
                            data-test-name={'equalsWarn-msg'}
                            fill
                            key={'equalsWarn-msg'}
                            type="warning"
                        >
                            {_(WARN_MSG_CONTAINS_EQUALS)}
                            <Link
                                to={props.learnMoreLink}
                                openInNewContext
                                data-test-name="equalsWarn.learnMoreLink"
                                style={{ whiteSpace: 'nowrap' }}
                            >
                                {_(' Learn More')}
                            </Link>
                        </Message>
                    )}
                    {fieldCollisionWarn && (
                        <Message
                            className="restrctionsMsg"
                            data-test-name={'fieldCollisionWarn-msg'}
                            fill
                            key={'fieldCollisionWarn-msg'}
                            type="warning"
                        >
                            {_(sprintf(WARN_MSG_FIELD_COLLISION, { field: props.idxFieldSelected }))}
                        </Message>
                    )}
                </ColumnLayout.Column>
            </ColumnLayout.Row>
            <ColumnLayout.Row data-test-name="restrictions-row" style={{ marginTop: '-25px', maxWidth: '1200px' }}>
                <ColumnLayout.Column data-test-name="generator-col" span={6} style={{ padding: 10, minHeight: 80 }}>
                    <Heading data-test-name="generator-heading" level={2}>
                        {_('Search filter generator')}
                    </Heading>
                    <ControlGroup
                        data-test-name="timerange-cg"
                        help={sprintf(_('Increasing the time range beyond the default of ' +
                            '%(defaultTime)s can increase the time it takes to populate the ' +
                            '"Indexed Fields" and "Values" text boxes.'), { defaultTime: DEFAULT_TIMERANGE_LABEL })}
                        label={_('Indexed field and values time range')}
                        labelPosition="top"
                    >
                        <Select
                            data-test-name="timerange-select"
                            defaultValue={DEFAULT_TIMERANGE}
                            disabled={props.disableGenerator}
                            name="srchTimerange"
                            onChange={props.handleSrchTimerangeChange}
                            style={{ maxWidth: '130px' }}
                            value={props.srchTimerange}
                        >
                            <Select.Option
                                data-test-name="timerangeOpt-default"
                                label={DEFAULT_TIMERANGE_LABEL}
                                value={DEFAULT_TIMERANGE}
                            />
                            <Select.Option data-test-name="timerangeOpt-1hr" label={_('One hour')} value={'-1h'} />
                            <Select.Option data-test-name="timerangeOpt-24hr" label={_('24 hours')} value={'-1d'} />
                            <Select.Option data-test-name="timerangeOpt-7days" label={_('7 days')} value={'-7d'} />
                        </Select>
                    </ControlGroup>
                    <ControlGroup
                        data-test-name="idxFields-cg"
                        label={_('Indexed fields')}
                        labelPosition="top"
                        tooltip={_('This drop-down list box shows the 250 most commonly found' +
                            ' fields. To select an unlisted field, type in its name.')}
                    >
                        <ComboBox
                            data-test-name="idxFields-cb"
                            disabled={props.disableGenerator}
                            inline
                            name="idxField"
                            onChange={props.handleFieldChange}
                            isLoadingOptions={props.isWorking}
                            loadingMessage={<WaitSpinner />}
                            placeholder={_('Select or type an indexed field...')}
                            value={props.idxFieldSelected}
                        >
                            {props.idxFields.map(field => (
                                <ComboBox.Option
                                    data-test-name={`idxFields-cb-opt-${field.field}`}
                                    value={field.field}
                                    key={`cb-opt-${field.field}`}
                                />
                            ))}
                        </ComboBox>
                    </ControlGroup>
                    <ControlGroup
                        data-test-name="idxFieldVals-cg"
                        help={_('You can type in custom values that do not appear in' +
                            ' the list, including wildcards. Example: "syslog_*"')}
                        label={_('Values')}
                        labelPosition="top"
                        tooltip={_('This drop-down list box shows the 250 most common ' +
                            'values in alphabetical order. To select an unlisted value, ' +
                            'type it in and choose it at the top of the list.')}
                    >
                        <Multiselect
                            allowNewValues
                            compact
                            data-test-name="idxFieldVals-ms"
                            disabled={!props.idxFieldSelected || props.disableGenerator}
                            inline
                            name="idxFieldVal"
                            isLoadingOptions={props.isWorking}
                            loadingMessage={<WaitSpinner />}
                            noOptionsMessage={_('No matches')}
                            onChange={props.handleValueChange}
                            controlledFilter
                            onFilterChange={props.handleValueFilter}
                            placeholder={sprintf(_('Select one or more %(fieldName)s values'),
                                { fieldName: props.idxFieldSelected })}
                            values={props.idxFieldValSelected}
                        >
                            {props.idxFieldVals.map(field => (
                                (has(field, props.idxFieldSelected)) && (
                                <Multiselect.Option
                                    data-test-name={`idxFieldVals-ms-opt-${field[props.idxFieldSelected]}`}
                                    key={`cb-opt-${field[props.idxFieldSelected]}`}
                                    label={field[props.idxFieldSelected]}
                                    value={field[props.idxFieldSelected]}
                                />)
                            ))}
                        </Multiselect>
                    </ControlGroup>
                    <ControlGroup
                        data-test-name="concat-cg"
                        label={_('Concatenation option')}
                        labelPosition="top"
                        tooltip={
                            <div style={{ maxWidth: '160px' }}>
                                {_('Determines how the search filter generator adds the generated filter' +
                                  ' to the existing search filter.')}
                            </div>
                        }
                    >
                        <Select
                            data-test-name="concat-select"
                            disabled={props.disableGenerator || props.disableConcat}
                            name="concatOption"
                            onChange={props.handleConcatOpt}
                            style={{ maxWidth: '75px' }}
                            value={props.concatOpt}
                        >
                            <Select.Option data-test-name="option-or" label={_('OR')} value="OR" />
                            <Select.Option data-test-name="option-and" label={_('AND')} value="AND" />
                            <Select.Option data-test-name="option-not" label={_('NOT')} value="NOT" />
                        </Select>
                    </ControlGroup>
                    <ControlGroup
                        data-test-name="genSrchFilter-cg"
                        label={_('Generated search filter')}
                        labelPosition="top"
                    >
                        <Text
                            data-test-name="genSrchFilter-text"
                            disabled
                            name="genSrchFilter"
                            multiline
                            rowsMin={3}
                            value={props.generatedSrchFilter}
                        />
                    </ControlGroup>
                </ColumnLayout.Column>
                <ColumnLayout.Column data-test-name="srchFilter-col" span={6} style={{ padding: 10, minHeight: 80 }}>
                    <Heading data-test-name="srchFilter-heading" level={2} style={{ display: 'inline-block' }}>
                        {_('Search filter')}
                    </Heading>
                    <ControlGroup
                        data-test-name="srchFilter-cg"
                        help={
                            <div>
                                <P className="roles-help-list" style={{ margin: '12px 0 0 0' }}>
                                    {_('Note: the search filter can only include:')}
                                </P>
                                <List
                                    className="roles-help-list"
                                    data-test-name="roles-help-list"
                                    style={{ margin: '0', paddingLeft: '1.5em' }}
                                >
                                    <List.Item className="roles-help-list">{_('source type')}</List.Item>
                                    <List.Item className="roles-help-list">{_('source')}</List.Item>
                                    <List.Item className="roles-help-list">{_('host')}</List.Item>
                                    <List.Item className="roles-help-list">{_('index')}</List.Item>
                                    <List.Item className="roles-help-list">{_('event type')}</List.Item>
                                    <List.Item className="roles-help-list">{_('search fields')}</List.Item>
                                    <List.Item className="roles-help-list">
                                        {_('the operators "*", "OR", "AND", "NOT"')}
                                    </List.Item>
                                </List>
                            </div>
                        }
                        label={_('Search filter')}
                        labelPosition="top"
                        hideLabel
                    >
                        <Text
                            data-test-name="srchFilter-text"
                            inline
                            multiline
                            name="srchFilter"
                            onChange={props.handleResourceChange}
                            placeholder={_('Enter a valid search filter here, or use the' +
                                ' search filter generator on the left to generate a search filter.')}
                            rowsMin={17}
                            rowsMax={17}
                            style={{ width: '100%', marginTop: '11px' }}
                            value={props.srchFilter}
                        />
                    </ControlGroup>
                </ColumnLayout.Column>
            </ColumnLayout.Row>
            <ColumnLayout.Row data-test-name="restrictions-btn-row" style={{ marginTop: '-30px', maxWidth: '1200px' }}>
                <ColumnLayout.Column data-test-name="generator-btn-col" span={6}>
                    <Button
                        appearance="primary"
                        data-test-name="apply-btn"
                        disabled={!props.idxFieldSelected || props.idxFieldValSelected.length === 0
                            || props.disableGenerator}
                        label={_('Add to search filter ')}
                        onClick={props.handleApplyClick}
                        style={{ height: '2em', margin: '0 0.5em 0 0.6em' }}
                    />
                    <Button
                        data-test-name="reset-btn"
                        disabled={props.disableGenerator}
                        label={_('Reset')}
                        onClick={props.handleResetClick}
                    />
                </ColumnLayout.Column>
                <ColumnLayout.Column data-test-name="srchFilter-btn-col" span={6}>
                    <Button
                        data-test-name="preview-results-btn"
                        openInNewContext
                        label={_('Preview search filter results')}
                        onClick={props.handlePreviewSrchFilter}
                        style={{ marginLeft: '0.7em' }}
                    />
                </ColumnLayout.Column>
            </ColumnLayout.Row>
        </ColumnLayout>
    );
};

Restrictions.propTypes = {
    concatOpt: PropTypes.string,
    disableConcat: PropTypes.bool,
    disableGenerator: PropTypes.bool,
    generatedSrchFilter: PropTypes.string,
    isWorking: PropTypes.bool,
    srchFilter: PropTypes.string.isRequired,
    srchTimerange: PropTypes.string,
    idxFields: PropTypes.arrayOf(PropTypes.shape({})),
    idxFieldSelected: PropTypes.string,
    idxFieldVals: PropTypes.arrayOf(PropTypes.shape({})),
    idxFieldValSelected: PropTypes.arrayOf(PropTypes.string),
    handleApplyClick: PropTypes.func.isRequired,
    handleConcatOpt: PropTypes.func.isRequired,
    handleFieldChange: PropTypes.func.isRequired,
    handleResetClick: PropTypes.func.isRequired,
    handleResourceChange: PropTypes.func.isRequired,
    handleSrchTimerangeChange: PropTypes.func.isRequired,
    handlePreviewSrchFilter: PropTypes.func.isRequired,
    handleValueChange: PropTypes.func.isRequired,
    handleValueFilter: PropTypes.func.isRequired,
    learnMoreLink: PropTypes.string.isRequired,
};

Restrictions.defaultProps = {
    concatOpt: 'OR',
    disableConcat: false,
    disableGenerator: false,
    generatedSrchFilter: '',
    isWorking: false,
    srchTimerange: '-60s',
    idxFields: [],
    idxFieldSelected: '',
    idxFieldVals: [],
    idxFieldValSelected: [],
};

export default Restrictions;
