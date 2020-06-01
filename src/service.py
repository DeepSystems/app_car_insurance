import concurrent.futures
from queue import Queue
import threading
import json

from supervisely_lib.worker_api.agent_api import AgentAPI
from supervisely_lib.worker_api.rpc_servicer import ConnectionClosedByServerException, REQUEST_ID
from supervisely_lib.task.progress import report_agent_rpc_ready
from supervisely_lib.worker_proto import worker_api_pb2 as api_proto
import supervisely_lib.io.json as sly_json
from supervisely_lib.function_wrapper import function_wrapper, function_wrapper_nofail
import traceback


REQUEST_DATA = "request_data"


class AppService:
    NETW_CHUNK_SIZE = 1048576
    QUEUE_MAX_SIZE = 2000  # Maximum number of in-flight requests to avoid exhausting server memory.

    def __init__(self, logger, task_config):
        self.logger = logger
        self.server_address = task_config['server_address']
        self.api = AgentAPI(token=task_config['agent_token'],
                            server_address=self.server_address,
                            ext_logger=self.logger)

        self.api.add_to_metadata('x-task-id', str(task_config['task_id']))

        self.routes = {}

        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.processing_queue = Queue(maxsize=self.QUEUE_MAX_SIZE)
        self.logger.debug('Created AgentRPCServicer', extra=task_config)

    def add_route(self, route, func):
        self.routes[route] = func

    def _processing(self):
        while True:
            request_msg = self.processing_queue.get(block=True, timeout=None)
            try:
                self.routes[request_msg["command"]](request_msg)
            except Exception as e:
                self.logger.error(traceback.format_exc(), exc_info=True, extra={'exc_str': str(e)})

    def run(self):
        def seq_inf_wrapped():
            function_wrapper(self._processing)  # exit if raised

        process_thread = threading.Thread(target=seq_inf_wrapped, daemon=True)
        process_thread.start()

        for gen_event in self.api.get_endless_stream('GetGeneralEventsStream', api_proto.GeneralEvent, api_proto.Empty()):
            try:
                data = {}
                if gen_event.data is not None and gen_event.data != b'':
                    data = json.loads(gen_event.data.decode('utf-8'))

                event_obj = {REQUEST_ID: gen_event.request_id, **data}
                self.processing_queue.put(event_obj, block=True)
            except Exception as error:
                self.logger.warning('App exception: ', extra={"error_message": str(error)})

        raise ConnectionClosedByServerException('Requests stream to a deployed model closed by the server.')