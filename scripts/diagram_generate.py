"""
REF: https://github.com/mingrammer/diagrams
REF: https://diagrams.mingrammer.com/docs/getting-started/examples
"""

from diagrams import Diagram
from diagrams import Cluster
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import Eventbridge
from diagrams.aws.integration import StepFunctions


from utils import common_utils
from utils import stepfunc_utils


def main():
    template = common_utils.get_template()
    func_map = {x['name']: x for x in template['resources'].get('lambda') or []}
    state_machines = {}
    if template['resources'].get('stepfunc'):
        for info in template['resources'].get('stepfunc') or []:
            specs = stepfunc_utils.render_state_machine(info['definition-path'])
            func_names = stepfunc_utils.get_state_machine_function_names(specs)
            state_machines[info['name']] = func_names
    with Diagram("Clustered Web Services", show=False, filename='/tmp/diagram'):
        stepfunc_map = {}
        for k, steps in state_machines.items():
            with Cluster('Step Function: ' + k):
                stepfunc_map[k] = [Lambda(s) for s in steps]
        for specs in template['resources'].get('schedule') or []:
            rule = Eventbridge('EventBridge: ' + specs['name'])
            if specs['target-type'] == 'lambda' and specs['target-name'] in func_map:
                rule >> Lambda(func_map[specs['target-name']]['name'])
            if specs['target-type'] == 'stepfunc' and specs['target-name'] in stepfunc_map:
                rule >> stepfunc_map[specs['target-name']]
    return


if __name__ == '__main__':
    main()

