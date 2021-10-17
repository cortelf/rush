import logging
from traceback import format_exc
from typing import Dict, BinaryIO, Union, List

from rush.utils.exceptions import NotFoundError
from rush.core.entities import Handler, Request, CaseInsensitiveDict

logger = logging.getLogger(__name__)


class HandlersManager:
    def __init__(self,
                 http_server,
                 loader, handlers: Dict[str, Handler],
                 err_handlers: Dict[str, callable],
                 redirects: [bytes, bytes],
                 auto_static_distribution: bool = True
                 ):
        self.loader = loader
        self.handlers = handlers
        self.err_handlers = err_handlers
        self.redirects = redirects  # from_path: response_with_new_path
        self.auto_static_distribution = auto_static_distribution

        self.request_obj = Request(http_server, loader)
        # some hardcoded binds for err handlers
        self.not_found_handler = err_handlers['not-found']
        self.internal_error_handler = err_handlers['internal-error']

    def call_handler(self,
                     response_http,
                     body: bytes,
                     conn: BinaryIO,
                     proto_version: str,
                     method: bytes,
                     path: bytes,
                     parameters: bytes,
                     fragment: bytes,
                     headers: CaseInsensitiveDict,
                     file: bool
                     ):
        if path in self.redirects:
            return response_http(conn, self.redirects[path])

        request_obj = self.request_obj
        request_obj.build(protocol=proto_version,
                          method=method,
                          path=path.decode(),
                          parameters=parameters,
                          fragment=fragment,
                          headers=headers,
                          body=body,
                          conn=conn,
                          file=file)

        if path.startswith(b'/static/') and self.auto_static_distribution:
            try:
                self.loader.send_response(conn, request_obj.path, None)
            except (NotFoundError, FileNotFoundError):
                self.not_found_handler(request_obj)
            finally:
                return request_obj

        handler = _pick_handler(self.handlers, request_obj)

        if handler is None:
            return self.not_found_handler(request_obj)

        try:
            handler(request_obj)
        except (FileNotFoundError, NotFoundError):
            self.not_found_handler(request_obj)
        except Exception as exc:
            logger.error('caught an unhandled exception in handler '
                         f'"{handler.__name__}": {exc}')
            logger.exception(f'detailed error trace:\n{format_exc()}')

            self.internal_error_handler(request_obj)
        finally:
            return request_obj


def err_handler_wrapper(
        err_handler_type: str,
        func: callable,
        request: Request
        ):
    try:
        func(request)
    except Exception as exc:
        logger.error(f'caught an unhandled exception in {err_handler_type} handler (function name: '
                     f'{func.__name__}): {exc}\nFull traceback:\n{format_exc()}')


def _filter_handlers(handlers: List[Handler], request: Request) -> Union[callable, None]:
    request_method = request.method

    for handler in handlers:
        if request_method not in handler.methods:
            continue

        if handler.filter and not handler.filter(request):
            continue

        return handler.func


def _pick_handler(handlers: Dict, request: Request) -> Union[callable, None]:
    """
    :param handlers: Dict[routing_path, Handler], but contains field `all: [Handler...]`
                     that contains list of handlers, which route all paths
    """

    if request.path not in handlers:
        return _filter_handlers(handlers[all], request)

    return handlers[request.path].func