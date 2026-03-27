class VTOBaseError(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class InvalidInputError(VTOBaseError):
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, "INVALID_REQUEST")


class PreprocessingError(VTOBaseError):
    def __init__(self, message: str = "Preprocessing failed"):
        super().__init__(message, "PREPROCESSING_FAILED")


class VRAMExhaustedError(VTOBaseError):
    def __init__(self, message: str = "GPU memory exhausted"):
        super().__init__(message, "SERVICE_DEGRADED")


class WorkerTimeoutError(VTOBaseError):
    def __init__(self, message: str = "Inference timed out"):
        super().__init__(message, "INFERENCE_TIMEOUT")


class ModelLoadError(VTOBaseError):
    def __init__(self, message: str = "Failed to load model"):
        super().__init__(message, "INTERNAL_ERROR")
