/**
 * Cloud version of data/indexes endpoint - does additonal clientside validation
 */
import IndexesModel from 'models/services/data/Indexes';
import { validationObj } from 'models/indexes/cloud/CloudIndexValidation';

export default IndexesModel.extend({
    validation: validationObj,
});