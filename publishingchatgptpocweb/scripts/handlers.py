import json
from queue import SimpleQueue
from typing import Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult

class LLMCallbackHandler(BaseCallbackHandler):
    def __init__(self, type, socketio=None):
        self.type = type
        self.socketio = socketio
        self.outputs = []
        self.queue = SimpleQueue()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.outputs.append(token)
        if self.socketio is not None:
            self.socketio.emit(f'{self.type}_response', {'status': 'sending partial response', 'type': self.type, 'text': token})
            print(f"{self.type} Type, Sending chunk: {token}")
        else:
            message_data = {'response': token}
            formatted_message = f"event: {self.type}\ndata: {json.dumps(message_data)}\n\n"
            self.queue.put(formatted_message)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        completion_data = {'status': 'complete'}
        completion_message = f'event: {self.type}\ndata: {json.dumps(completion_data)}\n\n'

        if self.socketio is not None:
            print(f"{type} Type Response Exited, sending completion status")
            self.socketio.emit(f'{self.type}_response', {'status': 'full response complete', 'type': self.type})  
        else:
            self.queue.put(completion_message)
            self.stop_event_stream()

    def event_stream(self):
        while True:
            data = self.queue.get()
            if data is None:
                break
            yield data

    def stop_event_stream(self):
        self.queue.put(None)

