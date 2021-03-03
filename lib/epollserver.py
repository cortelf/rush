import select
from threading import Thread
from socket import socket, MSG_PEEK


"""
EpollServer(addr: Tuple[str, int], maxconns: int = 0)

there are 4 types of events:
    CONNECT - on connect to server
    DISCONNECT - on disconnect of server
    RECEIVE - on receiving some data
    RESPONSE - on sending data
    
to handle the events, you need to have a function that receives only 2 arguments - event_type and conn
conn is a object of connection (logic) with some events
event_type is integer to compare with lib's constants

if handler handles connect events, it has to return new conn object

example:
```
import epollserver

epoll_server = epollserver.EpollServer(('localhost', 8080))


@epoll_server.handler(on_event=epollserver.CONNECT)
def connect_handler(_, server):
    conn, addr = server.accept()
    print('new conn:', addr)
    
    return conn
    

# OR
epoll_server.add_handler(connect_handler, on_event=epollserver.CONNECT)
```

default value of on_event is all (built-in name, yes, but it sounds cool)
if on_event was not changed, your handler will handle all the events
"""


CONNECT = 0
DISCONNECT = 1
RECEIVE = 2
RESPONSE = 3


class EpollServer:
    def __init__(self, addr, maxconns=0):
        self.server_sock = socket()
        self.epoll = select.epoll()
        self.handlers = {}  # epoll event: callable

        self.server_sock.bind(addr)
        self.server_sock.listen(maxconns)
        self.server_sock.setblocking(False)

        self._running = False
        self.conns = {}

    def add_handler(self, handler, on_event=all):
        self.handlers[on_event] = handler

    def start(self, threaded=False):
        if self._running:
            raise RuntimeError('server already started')

        if threaded:
            server_thread = Thread(target=self.start)
            server_thread.start()

            return server_thread

        self._running = True
        self.epoll.register(self.server_sock.fileno(), select.EPOLLIN)

        # _running is also a flag. Server will stop after _running will be set to False
        while self._running:
            events = self.epoll.poll(1)

            for fileno, event in events:
                event_type = self.get_event_type(fileno, event)

                if all in self.handlers:
                    handler = self.handlers[all]
                    handler(event_type, self.conns[fileno])
                    continue

                handler = self.handlers.get(event_type)

                if handler is None:
                    # no attached handlers registered
                    continue

                if event_type == CONNECT:
                    conn = handler(CONNECT, self.server_sock)
                    conn.setblocking(False)
                    conn_fileno = conn.fileno()
                    self.conns[conn_fileno] = conn
                    self.epoll.register(conn_fileno, select.EPOLLIN)
                elif event_type == DISCONNECT:
                    self.epoll.unregister(fileno)
                    conn = self.conns.pop(fileno)
                    handler(DISCONNECT, conn)
                else:
                    handler(event_type, self.conns[fileno])

    def get_event_type(self, fileno, event):
        if fileno == self.server_sock.fileno():
            return CONNECT
        elif event & select.EPOLLIN:
            try:
                peek_byte = self.conns[fileno].recv(1, MSG_PEEK)
            except ConnectionResetError:
                return DISCONNECT

            if not peek_byte:
                return DISCONNECT

            return RECEIVE
        elif event & select.EPOLLOUT:
            return RESPONSE
        elif event & select.EPOLLHUP:
            return DISCONNECT
        else:
            raise NotImplementedError('unavailable epoll signal: ' + str(event))

    def handler(self, on_event=all):
        def decorator(func):
            self.handlers[on_event] = func

            return func

        return decorator

    def stop(self):
        # max server alive-time after stopping is 1 second
        self._running = False
        self.epoll.close()
        self.server_sock.close()

    def __del__(self):
        self.stop()
