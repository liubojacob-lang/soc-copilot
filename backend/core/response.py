"""
统一响应格式和错误处理机制。

.. deprecated::
    本模块中的 ``APIException`` 已于 2026-08-11 废弃。
    请使用 ``core.exceptions.APIException`` + ``core.enums.error_codes.ErrorCode`` 替代。

    旧用法（已废弃）::
        from core.response import APIException
        raise APIException(code="INVALID_REQUEST", message="...", status_code=400)

    新用法::
        from core.exceptions import BadRequestException
        from core.enums.error_codes import ValidationError
        raise BadRequestException(ValidationError.INVALID_INPUT, details={"field": "..."})

    CI 保护规则：禁止新代码引入 ``from core.response import APIException``。
    如需 CI lint，请在 ``.pre-commit-config.yaml`` 中添加:
        - id: no-legacy-api-exception
          name: Block old APIException import
          entry: "from core.response import APIException"
          language: pygrep
          types: [python]
          exclude: '^core/response\\.py$'
          fail_found: true
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """错误详情模型。"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: dict[str, Any] | None = Field(None, description="详细错误信息")


class MetaInfo(BaseModel):
    """元信息模型。"""

    page: int | None = Field(None, description="当前页码")
    page_size: int | None = Field(None, description="每页大小")
    total: int | None = Field(None, description="总记录数")
    total_pages: int | None = Field(None, description="总页数")
    took: float | None = Field(None, description="响应时间(ms)")
    version: str = Field("1.0", description="API版本")


class APIResponse(BaseModel, Generic[T]):
    """统一API响应格式。"""

    success: bool = Field(..., description="请求是否成功")
    data: T | None = Field(None, description="响应数据")
    error: ErrorDetail | None = Field(None, description="错误信息")
    meta: MetaInfo | None = Field(None, description="元信息")

    class Config:
        """Pydantic配置。"""

        arbitrary_types_allowed = True


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式。"""

    items: list[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


# ============================================================================
# DEPRECATED: APIException (2026-08-11)
#
# 此类已废弃，统一使用 ``core.exceptions.APIException``。
# 保留注释版本以便历史参考。迁移完成后可以安全删除。
# ============================================================================

# class APIException(Exception):
#     """API异常类。[DEPRECATED] 请使用 core.exceptions.APIException"""
#
#     def __init__(
#         self,
#         code: str,
#         message: str,
#         status_code: int = 400,
#         details: dict[str, Any] | None = None,
#     ):
#         """初始化API异常。"""
#         self.code = code
#         self.message = message
#         self.status_code = status_code
#         self.details = details
#         super().__init__(message)


# 常用错误码
ERROR_CODES = {
    "INVALID_REQUEST": "无效的请求参数",
    "AUTHENTICATION_FAILED": "认证失败",
    "AUTHORIZATION_FAILED": "权限不足",
    "RESOURCE_NOT_FOUND": "资源不存在",
    "DATABASE_ERROR": "数据库操作失败",
    "SERVICE_ERROR": "服务内部错误",
    "VALIDATION_ERROR": "数据验证失败",
    "RATE_LIMIT_EXCEEDED": "请求频率过高",
    "CSRF_TOKEN_INVALID": "CSRF令牌无效",
    "TOKEN_EXPIRED": "令牌已过期",
    "TOKEN_INVALID": "令牌无效",
    "INTERNAL_SERVER_ERROR": "服务器内部错误",
    "NETWORK_ERROR": "网络错误",
    "TIMEOUT_ERROR": "请求超时",
    "CONFLICT_ERROR": "资源冲突",
    "UNPROCESSABLE_ENTITY": "无法处理的实体",
}


def create_success_response(
    data: Any = None, meta: MetaInfo | None = None
) -> APIResponse:
    """创建成功响应。"""
    return APIResponse(success=True, data=data, error=None, meta=meta)


def create_error_response(
    code: str,
    message: str | None = None,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
) -> APIResponse:
    """创建错误响应。"""
    if not message:
        message = ERROR_CODES.get(code, "未知错误")

    return APIResponse(
        success=False,
        data=None,
        error=ErrorDetail(code=code, message=message, details=details),
        meta=None,
    )


def create_paginated_response(
    items: list[Any], total: int, page: int, page_size: int
) -> APIResponse:
    """创建分页响应。"""
    total_pages = (total + page_size - 1) // page_size

    paginated_data = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    meta = MetaInfo(
        page=page, page_size=page_size, total=total, total_pages=total_pages
    )

    return APIResponse(success=True, data=paginated_data, error=None, meta=meta)
