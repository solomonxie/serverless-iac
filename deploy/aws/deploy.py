from deploy_lambda import LambdaDeployHelper
from deploy_rest_api import RestApiDeployHelper
from deploy_step_function import StepFuncDeployHelper
from deploy_schedules import ScheduleDeployHelper


def main():
    LambdaDeployHelper().deploy()
    RestApiDeployHelper().deploy()
    StepFuncDeployHelper().deploy()
    ScheduleDeployHelper().deploy()


if __name__ == '__main__':
    main()
