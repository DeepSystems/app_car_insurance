import os
import supervisely_lib as sly
import supervisely_lib.io.json as sly_json


def get_task_api():
    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
    task_info = sly_json.load_json_file(os.path.join(SCRIPT_DIR, "../task_config.json"))
    task_id = task_info["task_id"]
    server_address = task_info["server_address"]
    api_token = task_info["api_token"]
    api = sly.Api(server_address, api_token, retry_count=10)
    api.add_additional_field('taskId', task_id)
    api.add_header('x-task-id', str(task_id))
    return task_id, api