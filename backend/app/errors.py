from dataclasses import dataclass


@dataclass(slots=True)
class NormalizedProviderError:
    provider: str
    operation: str
    status: str
    message: str
    retryable: bool
    raw_error_summary: str


class ProviderError(Exception):
    def __init__(
        self,
        *,
        provider: str,
        operation: str,
        message: str,
        retryable: bool = False,
        raw_error_summary: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.operation = operation
        self.message = message
        self.retryable = retryable
        self.raw_error_summary = (raw_error_summary or message)[:500]
        self.status_code = status_code

    def normalized(self) -> NormalizedProviderError:
        return NormalizedProviderError(
            provider=self.provider,
            operation=self.operation,
            status="failed",
            message=self.message,
            retryable=self.retryable,
            raw_error_summary=self.raw_error_summary,
        )
