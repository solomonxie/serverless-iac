from aws.deploy_lambda import LambdaDeployHelper
from aws.deploy_rest_api import RestApiDeployHelper
from aws.deploy_step_function import StepFuncDeployHelper
from aws.deploy_schedules import ScheduleDeployHelper


def main():
    LambdaDeployHelper().deploy()
    RestApiDeployHelper().deploy()
    StepFuncDeployHelper().deploy()
    ScheduleDeployHelper().deploy()


if __name__ == '__main__':
    main()
