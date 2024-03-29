import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, final

from jsonic_rpc._internal.abstractions.exception_handling import (
    BaseExceptionConfiguration,
)
from jsonic_rpc._internal.abstractions.exceptions import (
    InternalError,
    InvalidRequest,
    JsonRpcError,
)
from jsonic_rpc._internal.abstractions.serializing import (
    BaseDumper,
    BaseLoader,
)
from jsonic_rpc._internal.types import (
    InputMapping,
    Notification,
    OutputMapping,
    Request,
    Response,
)

Context = TypeVar("Context")


logger = logging.getLogger("jsonic_rpc")


class BaseProcessor(ABC, Generic[Context]):
    loader: BaseLoader
    dumper: BaseDumper
    exception_configuration: BaseExceptionConfiguration

    @abstractmethod
    def _process_request(
        self,
        request: Request,
        context: Context | None,
    ) -> Response:
        ...

    @abstractmethod
    def _process_notification(
        self,
        message: Notification,
        context: Context | None,
    ) -> None:
        ...

    @abstractmethod
    async def _async_process_request(
        self,
        request: Request,
        context: Context | None,
    ) -> Response:
        ...

    @abstractmethod
    async def _async_process_notification(
        self,
        message: Notification,
        context: Context | None,
    ) -> None:
        ...

    @final
    def _process_exception(
        self, exc: Exception, message: Request, data: InputMapping
    ) -> OutputMapping:
        filter_result = self.exception_configuration.filter_map(exc)
        if filter_result is not None:
            return self.exception_configuration.dump(
                self.dumper, filter_result, message
            )
        logger.exception(
            "Unexpected exception", exc_info=exc, extra={"data": data}
        )
        return self.dumper.dump_exception(
            InternalError(message="Unexpected error", data=data), message
        )

    @final
    def process_single(
        self,
        data: InputMapping,
        context: Context | None = None,
    ) -> OutputMapping | None:
        try:
            message = self.loader.load_message(data)
        except InvalidRequest as exc:
            return self.dumper.dump_exception(exc)

        if isinstance(message, Notification):
            try:
                self._process_notification(message, context)
            except Exception as exc:
                logger.exception(
                    "Unexpected exception", exc_info=exc, extra={"data": data}
                )
            return None

        try:
            response = self._process_request(message, context)
            return self.dumper.dump_response(response)

        except JsonRpcError as exc:
            return self.dumper.dump_exception(exc, message)

        except Exception as exc:
            return self._process_exception(exc, message, data)

    @final
    async def async_process_single(
        self,
        data: InputMapping,
        context: Context | None = None,
    ) -> OutputMapping | None:
        try:
            message = self.loader.load_message(data)
        except InvalidRequest as exc:
            return self.dumper.dump_exception(exc)

        if isinstance(message, Notification):
            try:
                await self._async_process_notification(message, context)
            except Exception as exc:
                logger.exception(
                    "Unexpected exception", exc_info=exc, extra={"data": data}
                )
            return None

        try:
            response = await self._async_process_request(message, context)
            return self.dumper.dump_response(response)

        except JsonRpcError as exc:
            return self.dumper.dump_exception(exc, message)

        except Exception as exc:
            return self._process_exception(exc, message, data)
