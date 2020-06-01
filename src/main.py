import os
import time
_start = time.time()
import supervisely_lib as sly
import supervisely_lib.io.json as sly_json
import utils
from service import AppService
import numpy as np
import cv2


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

labeling_config = sly_json.load_json_file(os.path.join(SCRIPT_DIR, "../labeling_config.json"))
cases = sly_json.load_json_file(os.path.join(SCRIPT_DIR, '../cases.json'))

sides = ["front", "back", "left", "right"]
projects = {}

team_id = 1
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
    partsLabelingUrl = []
    draw_image_ids = []

    for side in sides:
        dataset = api.dataset.get_or_create(projects[side].id, str(case["id"]))
        try:
            image_info = api.image.upload_link(dataset.id, "{}.png".format(case["id"]), case[side])
            url = api.image.url(team_id, labeling_workspace_id, projects[side].id, dataset.id, image_info.id)
            draw_image_ids.append({"side": side, "image_id": image_info.id, "image_url": case[side]})
            partsLabelingUrl.append(url)
        except Exception as e:
            print(e)
            pass
    api.task.set_data(task_id, 2, "state.active")

    partsAnnotations = []
    for url in get_case_urls(case):
        partsAnnotations.append([[url, url]])

    api.task.set_data(task_id, {"partsLabelingUrl": partsLabelingUrl,
                                "drawImageIds": draw_image_ids,
                                "partsAnnotations": partsAnnotations}, "data", append=True)


def get_case_urls(case):
    case_urls = []
    for side in sides:
        case_urls.append(case[side])
    return case_urls


def refresh_parts(request):

    parts_annotations = []

    draw_image_ids = api.task.get_data(task_id, "data.drawImageIds")
    for draw_obj in draw_image_ids:
        image_id = draw_obj["image_id"]
        side = draw_obj["side"]
        image_url = draw_obj["image_url"]

        meta_json = api.project.get_meta(projects[side].id)
        meta = sly.ProjectMeta.from_json(meta_json)

        ann_json = api.annotation.download(image_id).annotation
        ann = sly.Annotation.from_json(ann_json, meta)
        render = np.zeros(ann.img_size + (3,), dtype=np.uint8)
        alpha = np.zeros(ann.img_size + (1,), dtype=np.uint8)
        ann.draw(render)
        ann.draw(alpha, color=[255])
        rgba = np.concatenate((render, alpha), axis=2)


        bgra = rgba[..., [2, 1, 0, 3]]
        #sly.image.write("/workdir/src/01.png", rgba, remove_alpha_channel=False)

        parts_annotations.append([[image_url, sly.image.np_image_to_data_url(bgra)]])

    api.task.set_data(task_id, parts_annotations, "data.partsAnnotations")
    print(parts_annotations)

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
        "dialogTableVisible": False,
        "dialogTableVisible2": False
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
    app_service.add_route("refresh_parts", refresh_parts)
    app_service.run()


if __name__ == "__main__":
    main()
    sly.logger.info("SCRIPT_TIME {}: {} sec".format(os.path.basename(__file__), time.time() - _start))
