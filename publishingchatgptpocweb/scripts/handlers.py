import json
from queue import SimpleQueue
from typing import Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from typing import Union

class LLMCallbackHandler(BaseCallbackHandler):
    def __init__(self, sessionId):
        self.sessionId = sessionId
        self.outputs = []
        self.queue = SimpleQueue()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.outputs.append(token)
        message_data = {'sessionId': self.sessionId, 'response': token}
        formatted_message = f"event: llmstream\ndata: {json.dumps(message_data)}\n\n"
        self.queue.put(formatted_message)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        completion_data = {'sessionId': self.sessionId, 'status': 'complete'}
        completion_message = f'event: llmstream\ndata: {json.dumps(completion_data)}\n\n'
        self.queue.put(completion_message)
        self.stop_event_stream()

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        self.send_error_event(str(error))

    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        self.send_error_event(str(error))

    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        self.send_error_event(str(error))

    def send_error_event(self, error_message: str):
        error_data = {
            'sessionId': self.sessionId, 
            'status': 'error', 
            'message': error_message
        }
        error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
        self.queue.put(error_event)
        self.stop_event_stream()

    def event_stream(self):
        while True:
            data = self.queue.get()
            if data is None:
                break
            yield data

    def stop_event_stream(self):
        self.queue.put(None)

