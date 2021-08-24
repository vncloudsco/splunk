/* eslint-disable class-methods-use-this */
import React from 'react';
import Button from '@splunk/react-ui/Button';
import Dropdown from '@splunk/react-ui/Dropdown';
import Menu from '@splunk/react-ui/Menu';
import Heading from '@splunk/react-ui/Heading';
import Switch from '@splunk/react-ui/Switch';
import { _ as i18n } from '@splunk/ui-utils/i18n';
import { sprintf } from '@splunk/ui-utils/format';
import _ from 'underscore';
import PropTypes from 'prop-types';

const cssStyles = {
    containor: {
        padding: '20p',
        width: '100%',
        display: 'block',
        position: 'relative',
    },
    wrap: {
        whiteSpace: 'pre-wrap',
    },
    headerSection: {
        display: 'flex',
        position: 'relative',
        minHeight: '30px',
        flex: '0 0 auto',
        padding: '10px 20px 5px 20px',
        borderBottom: '1px solid #C3CBD4',
    },
    headerText: {
        margin: '4px 20px 0 0',
    },
    tableSection: {
        marginLeft: '9px',
        marginRight: '9px',
     //   textAlign: 'center',
        overflowY: 'auto',
        height: '90vh',
    },
    dropdownCount: {
        verticalAlign: 'middle',
        flex: '0 0 auto',
        margin: 0,
        float: 'right',
    },
    errorMessage: {
        color: '#3c444d',
        paddingTop: 100,
        minHeight: 400,
   //     textAlign: 'center',
    },
    targetRow: {
        fontWeight: 'bolder',
        overflowWrap: 'normal',
        backgroundColor: 'yellow',
    },
    tableRow: {
        border: 0,
        margin: 0,
        padding: 0,
        whiteSpace: 'nowrap',
    },
};


export default class ShowSource extends React.Component {

    constructor(props) {
        super(props);
        this.ref = React.createRef();
        this.state = {
            count: props.count,
            wrap: false,
        };
    }

    componentDidMount() {
        this.scroll();
    }

    componentDidUpdate() {
        this.scroll();
    }

    scroll() {
        if (this.ref.current) {
            this.ref.current.scrollIntoView({
                block: 'center',
                inline: 'center',
            });
        }
    }

    limitClick(count) {
        return () => {
            this.setState({ count });
        };
    }

    toggleWrap = () => {
        const { wrap } = this.state;
        this.setState({ wrap: !wrap });
    }

    renderLimitDropdown(count) {
        const toggle = (<Button
            label={sprintf(i18n('Number of Results: %(count)d'), { count })}
            isMenu
            appearance="pill"
        />);
        const limits = [10, 25, 50, 100, 1000];

        return (<Dropdown toggle={toggle} style={cssStyles.dropdownCount}>
            <Menu style={{ width: 120 }}>
                {limits.map(limit => <Menu.Item key={limit} onClick={this.limitClick(limit)}>
                    {limit}
                </Menu.Item>)}
            </Menu>
        </Dropdown>);
    }
    renderError(error) {
        return (
            <div data-component="showsource:view" className="ShowSource" >
                <div style={cssStyles.errorMessage} className="sourceText">{error.statusText}</div>
            </div>
        );
    }

    render() {
        const { events, error, textStrings } = this.props;
        const { count, wrap } = this.state;

        let eventList = _.where(events, event => event.MSG_CONTENT);
        const offset = _.indexOf(eventList.map(e => e.isTarget), true);
        eventList = eventList.splice(Math.max(0, offset - Math.floor(count / 2)))
                      .splice(0, count);
        const messages = _.reject(events, event => event.MSG_CONTENT);
        if (error) {
            return this.renderError(error);
        }

        if (events && !events.length) {
            return this.renderError({ statusText: textStrings.noContent });
        }

        const calculatedRowStyle = { ...cssStyles.tableRow, ...(wrap ? cssStyles.wrap : undefined) };

        const wrapResultsText = i18n('Wrap results');

        return (
            <div data-component="showsource:view" className="ShowSource" >
                <div key="header" style={cssStyles.containor} ><div style={cssStyles.headerSection}>

                    <Heading level={1} style={cssStyles.headerText}>{textStrings.heading}</Heading>
                    {this.renderLimitDropdown(count)}
                    <Switch
                        key="wrap-results"
                        onClick={this.toggleWrap}
                        selected={wrap}
                        appearance="toggle"
                        data-test-value="wrap-results"
                        aria-label={wrapResultsText}
                    >
                        {wrapResultsText}
                    </Switch>
                </div>

                    <div key="body" style={cssStyles.tableSection}>
                        {messages.map(row => (
                            <div
                                data-component="showsource:tableRow"
                                style={{ ...cssStyles.tableRow }}
                            >
                                {row.MSG_CONTENT}
                            </div>
                        ))}

                        {eventList.map((row, index) => {
                            if (row.isTarget) {
                                return (
                                    <div
                                        data-component="showsource:tableRow"
                                        className="SourceLine SourceLineHL"
                                        ref={this.ref}
                                        // eslint-disable-next-line react/no-array-index-key
                                        key={`key-${index}`}
                                    >
                                        <pre
                                            data-component="showsource:targetRow"
                                            className="sourceText"
                                            style={{ ...calculatedRowStyle, ...cssStyles.targetRow }}
                                        >
                                            {row.value}
                                        </pre>
                                    </div>);
                            }
                            return (
                                <div
                                    data-component="showsource:tableRow"
                                    className="SourceLine"
                                    // eslint-disable-next-line react/no-array-index-key
                                    key={`key-${index}`}
                                >
                                    <pre
                                        className="sourceText"
                                        style={calculatedRowStyle}
                                    >
                                        {row.value}
                                    </pre>
                                </div>);
                        })}
                    </div>
                </div>
            </div>);
    }

}

ShowSource.propTypes = {
    events: PropTypes.arrayOf(PropTypes.object),
    error: PropTypes.shape({ statusText: PropTypes.string }),
    count: PropTypes.number,
    textStrings: PropTypes.shape({
        noContent: PropTypes.string,
        heading: PropTypes.string,
    }),
};

ShowSource.defaultProps = {
    textStrings: {
        noContent: 'No Content.',
        heading: 'Show Source',
    },
    events: [],
    count: 25,
    error: null,
};

