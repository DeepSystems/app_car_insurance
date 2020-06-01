import os
import time
_start = time.time()
import supervisely_lib as sly
import supervisely_lib.io.json as sly_json
import utils
from service import AppService
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

labeling_config = sly_json.load_json_file(os.path.join(SCRIPT_DIR, "../labeling_config.json"))
cases = sly_json.load_json_file(os.path.join(SCRIPT_DIR, '../cases.json'))

sides = ["front", "back", "left", "right"]
projects = {}

result_workspace_id = 6
labeling_workspace_id = 7

task_id, api, task_config = utils.get_task_api()


def clean_workspace(workspace_id):
    projects = api.project.get_list(workspace_id)
    for project in projects:
        api.project.remove(project.id)


def init_workspace():
    clean_workspace(result_workspace_id)
    clean_workspace(labeling_workspace_id)

    def create_project(workspace_id, name):
        project = api.project.get_info_by_name(workspace_id, name)
        if project is not None:
            api.project.remove(project.id)
        project = api.project.create(workspace_id, name)
        return project

    for side in sides:
        classes = [sly.ObjClass(class_name, sly.AnyGeometry) for class_name in labeling_config[side]]
        projects[side] = create_project(labeling_workspace_id, side)
        meta = sly.ProjectMeta()
        meta = meta.add_obj_classes(classes)
        meta = meta.add_tag_metas([sly.TagMeta("case_id", sly.TagValueType.ANY_STRING),
                                   sly.TagMeta("validation", sly.TagValueType.ONEOF_STRING, possible_values=["accepted", "rejected"]),
                                   sly.TagMeta("finished", sly.TagValueType.NONE)])
        api.project.update_meta(projects[side].id, meta.to_json())


def accept_case(request):
    case_index = api.task.get_data(task_id, "data.caseIndex")
    case = cases[case_index]
    for side in sides:
        dataset = api.dataset.get_or_create(projects[side].id, str(case["id"]))
        api.image.upload_link(dataset.id, "{}.png".format(case["id"]), case[side])


def get_case_urls(case):
    case_urls = []
    for side in sides:
        case_urls.append(case[side])
    return case_urls


def main():

    with open(os.path.join(SCRIPT_DIR, 'gui.html'), 'r') as file:
        gui_template = file.read()



    #data
    data = {
        "caseId": cases[0]["id"],
        "caseIndex": 0,
        "sideUrls": get_case_urls(cases[0]),
        "sideCaptions": [side.upper() for side in sides],
        "partsLabelingUrl": ["a", "b", "c", "d"],
        "defectsLabelingUrl": ["x", "y", "y", "z"],
    }

    #state
    state = {
        "sideAccepted": [True] * len(sides),
        "active": 1,
        "frontAccept": True,
        "backAccept": True,
        "leftAccept": True,
        "rightAccept": True,
        "selectedImageIndex": 0,
        "dialogTableVisible": False
    }

    payload = {
        sly.app.TEMPLATE: gui_template,
        sly.app.STATE: state,
        sly.app.DATA: data,
    }

    init_workspace()

    #http://78.46.75.100:11111/apps/sessions/20
    jresp = api.task.set_data(task_id, payload)

    app_service = AppService(sly.logger, task_config)
    app_service.add_route("accept_case", accept_case)
    app_service.run()

    x = 10


if __name__ == "__main__":
    main()
    sly.logger.info("SCRIPT_TIME {}: {} sec".format(os.path.basename(__file__), time.time() - _start))
