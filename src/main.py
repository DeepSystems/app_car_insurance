import os
import time
_start = time.time()
import supervisely_lib as sly
import supervisely_lib.io.json as sly_json
import utils

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def main():
    task_id, api = utils.get_task_api()

    with open(os.path.join(SCRIPT_DIR, 'gui.html'), 'r') as file:
        gui_template = file.read()

    #data
    data = {
    }

    #state
    state = {
    }

    payload = {
        sly.app.TEMPLATE: gui_template,
        sly.app.STATE: state,
        sly.app.DATA: data,
    }

    #http://192.168.1.42/apps/sessions/130
    jresp = api.task.set_data(task_id, payload)


if __name__ == "__main__":
    main()
    sly.logger.info("SCRIPT_TIME {}: {} sec".format(os.path.basename(__file__), time.time() - _start))
