from typing import Generic, Optional, TypeVar
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse

T = TypeVar("T")


class APIOutput(BaseModel, Generic[T]):
    """
    Standard API response model
    """

    status_code: int
    message: str
    data: Optional[T] = None

    @staticmethod
    def success(
        data: Optional[T] = None,
        message: str = "Success",
        status_code: int = 200,
    ) -> JSONResponse:
        """
        Return a success JSON response
        """
        return JSONResponse(
            status_code=status_code,
            content=APIOutput(
                status_code=status_code,
                message=message,
                data=data,
            ).model_dump(),
        )

    @staticmethod
    def failure(
        message: str = "Internal Server Error",
        status_code: int = 500,
        data: Optional[T] = None,
    ) -> JSONResponse:
        """
        Return a failure JSON response
        """
        return JSONResponse(
            status_code=status_code,
            content=APIOutput(
                status_code=status_code,
                message=message,
                data=data,
            ).model_dump(),
        )

    @staticmethod
    def file(
        file_path: str,
        filename: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> FileResponse:
        """
        Return a file response (download / stream)
        """
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
        )
