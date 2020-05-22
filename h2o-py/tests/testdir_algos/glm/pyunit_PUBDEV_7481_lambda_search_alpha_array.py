import sys
sys.path.insert(1,"../../../")
import h2o
from tests import pyunit_utils
from h2o.estimators.glm import H2OGeneralizedLinearEstimator as glm

# with lambda_search enable and warm start, the model built with lambda search and with separate lambda/alpha values
# and previous beta should be close
def glm_alpha_lambda_arrays():
    # read in the dataset and construct training set (and validation set)
    d = h2o.import_file(path=pyunit_utils.locate("smalldata/logreg/prostate.csv"))
    mL = glm(family='binomial',lambda_search=True, alpha=[0.1,0.5,0.9],solver='COORDINATE_DESCENT')
    mL.train(training_frame=d,x=[2,3,4,5,6,7,8],y=1)
    r = glm.getGLMRegularizationPath(mL)
    regKeys = ["alphas", "lambdas", "explained_deviance_valid", "explained_deviance_train"]
    best_submodel_index = mL._model_json["output"]["best_submodel_index"]
    m2 = glm.makeGLMModel(model=mL,coefs=r['coefficients'][best_submodel_index])
    dev1 = r['explained_deviance_train'][best_submodel_index]
    p2 = m2.model_performance(d)
    dev2 = 1-p2.residual_deviance()/p2.null_deviance()
    print(dev1," =?= ",dev2)
    assert abs(dev1 - dev2) < 1e-6
    startVal = [0,0,0,0,0,0,0,-0.3945120960889672]
    orderedCoeffNames = ["AGE", "RACE", "DPROS", "DCAPS", "PSA", "VOL", "GLEASON", "Intercept"]
    for l in range(0,len(r['lambdas'])):
        m = glm(family='binomial',alpha=[r['alphas'][l]],Lambda=r['lambdas'][l],solver='COORDINATE_DESCENT', 
                startval=startVal)
        m.train(training_frame=d,x=[2,3,4,5,6,7,8],y=1)
        mr = glm.getGLMRegularizationPath(m)
        cs = r['coefficients'][l]
        cs_norm = r['coefficients_std'][l]
        pyunit_utils.assertEqualCoeffDicts(cs, m.coef())
        pyunit_utils.assertEqualCoeffDicts(cs_norm, m.coef_norm())
        startVal = extractNextCoeff(cs_norm, orderedCoeffNames, startVal) # prepare startval for next round
        p = m.model_performance(d)
        devm = 1-p.residual_deviance()/p.null_deviance()
        devn = r['explained_deviance_train'][l]
        print(devm)
        print(devn)
        assert abs(devm - devn) < 1e-4
        pyunit_utils.assertEqualRegPaths(regKeys, r, l, mr) # check all values from regPaths
        if (l == best_submodel_index): # check training metrics, should equal for best submodel index
            pyunit_utils.assertEqualModelMetrics(m._model_json["output"]["training_metrics"],
                                    mL._model_json["output"]["training_metrics"])
        else: # for other submodel, should have worse residual_deviance() than best submodel
            assert p.residual_deviance() >= p2.residual_deviance(), "Best submodel does not have lowerest " \
                                                                    "residual_deviance()!" 

def extractNextCoeff(cs_norm, orderedCoeffNames, startVal):
    for ind in range(0, len(startVal)):
        startVal[ind] = cs_norm[orderedCoeffNames[ind]]
    return startVal
    
if __name__ == "__main__":
    pyunit_utils.standalone_test(glm_alpha_lambda_arrays)
else:
    glm_alpha_lambda_arrays()
