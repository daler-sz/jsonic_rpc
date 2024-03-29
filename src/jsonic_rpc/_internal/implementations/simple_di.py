from inspect import Parameter, signature
from typing import Annotated, Any, Iterable, Mapping, TypeVar, get_args

from jsonic_rpc._internal.abstractions.di import (
    BaseDiInjector,
    DependsMetadata,
)
from jsonic_rpc._internal.abstractions.method import (
    AsyncRegisteredMethod,
    RegisteredMethod,
    SyncRegisteredMethod,
)
from jsonic_rpc._internal.abstractions.serializing import BaseLoader
from jsonic_rpc._internal.method_introspection import (
    method_depends_args,
    method_non_depends_args,
)
from jsonic_rpc._internal.types import Params, Result

T = TypeVar("T")
Dependency = Annotated[T, DependsMetadata]


class SimpleDiInjector(BaseDiInjector[dict]):
    """Silly di container. Not recommended for production"""

    def __init__(self, container: Mapping[Any, Any]):
        self.container = container

    def _load_args(
        self, method: RegisteredMethod, loader: BaseLoader, params: Params
    ) -> tuple[Iterable[Any], Mapping[str, Any]]:
        method_signature = signature(method.origin)

        non_dep_args = method_non_depends_args(method_signature)
        dep_args = method_depends_args(method_signature)

        loaded_args = loader.load_args(method, non_dep_args, params)
        deps = {}

        for dep_arg in dep_args:
            if dep_arg.kind == Parameter.POSITIONAL_ONLY:
                raise TypeError(
                    "Positional only DI dependencies are not supported"
                )

            tp = get_args(dep_arg.annotation)[0]
            dep = self.container[tp]
            deps[dep_arg.name] = dep
        return loaded_args.positionals, {**loaded_args.keywords, **deps}

    def call_injected(
        self,
        method: SyncRegisteredMethod,
        loader: BaseLoader,
        params: Params,
        context: dict | None,
    ) -> Result:
        if not context:
            context = {}

        positionals, keywords = self._load_args(method, loader, params)
        return method.origin(*positionals, **keywords, **context)

    async def async_call_injected(
        self,
        method: AsyncRegisteredMethod,
        loader: BaseLoader,
        params: Params,
        context: dict | None,
    ) -> Result:
        if not context:
            context = {}

        positionals, keywords = self._load_args(method, loader, params)
        return await method.origin(*positionals, **keywords, **context)
