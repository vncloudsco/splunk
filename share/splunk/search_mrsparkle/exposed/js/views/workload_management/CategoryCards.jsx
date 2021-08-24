import _ from 'underscore';
import React from 'react';
import Card from '@splunk/react-ui/Card';
import PropTypes from 'prop-types';
import css from './WorkloadManagement.pcssm';

function Categories(props) {
    const {
        handleCategoryClick,
        categoryCardState,
        categories,
    } = props;
    return (
        <div className={css.categoryCardContainer} data-test="categoryCardContainer">
            {categories.map(row => (
                <Card
                    className={css.categoryCard}
                    key={row.getName()}
                    value={row.getName()}
                    selected={categoryCardState.selected === row.getName()}
                    onClick={handleCategoryClick}
                >
                    <Card.Header title={row.getLabel()} />
                    {row.getCategory() !== 'all' ?
                        <Card.Body className={css.categoryCardBody}>
                            <div
                                className={css.categoryCardBodyDiv}
                                data-test="categoryCardBodyCpu"
                            >
                                <div>
                                    <span className={css.categoryCardValue}>
                                        {row.getCpuWeight()} / {row.getCpuWeightSum()}
                                    </span>
                                </div>
                                <div className={css.categoryCardText}>{_('CPU Weight').t()}</div>
                            </div>
                            <div
                                className={css.categoryCardBodyDiv}
                                data-test="categoryCardBodyMemory"
                            >
                                <div>
                                    <span className={css.categoryCardValue}>{row.getMemWeight()}%</span>
                                </div>
                                <div className={css.categoryCardText}>{_('Memory Limit %').t()}</div>
                            </div>
                        </Card.Body> : null
                    }
                </Card>
            ))}
        </div>
    );
}

Categories.propTypes = {
    handleCategoryClick: PropTypes.func.isRequired,
    categoryCardState: PropTypes.shape({}).isRequired,
    categories: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
};

export default Categories;
