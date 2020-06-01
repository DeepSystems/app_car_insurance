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


    cases = sly_json.load_json_file(os.path.join(SCRIPT_DIR, '../cases.json'))

    #data
    data = {
        "case": cases[0]
    }

    #state
    state = {
        "active": 1,
        "frontAccept": True,
        "backAccept": True,
        "leftAccept": True,
        "rightAccept": True,
    }

    payload = {
        sly.app.TEMPLATE: gui_template,
        sly.app.STATE: state,
        sly.app.DATA: data,
    }

    #http://78.46.75.100:11111/apps/sessions/20
    jresp = api.task.set_data(task_id, payload)


if __name__ == "__main__":
    main()
    sly.logger.info("SCRIPT_TIME {}: {} sec".format(os.path.basename(__file__), time.time() - _start))
