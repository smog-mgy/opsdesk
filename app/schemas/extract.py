from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, description="用户的报修/咨询描述原文")


class RequestType(str, Enum):
    REPORT = "报修"
    INQUIRY = "咨询"
    COMPLAINT = "投诉"
    OTHER = "其他"


class TicketExtract(BaseModel):
    """从用户报修/咨询描述中提取的结构化工单。"""

    ticket_id: str | None = Field(
        default=None, description="工单号,原文未出现则为 null,禁止编造"
    )
    request_type: RequestType = Field(description="用户诉求类型")
    expected_solution: str = Field(description="用户期望的处理方案,一句话概括")

    @field_validator("ticket_id", mode="before")
    @classmethod
    def _normalize_missing_ticket_id(cls, v: object) -> object:
        # 模型偶尔把"没有工单号"表达成占位字符串而非省略参数,统一归一为 None
        if isinstance(v, str) and v.strip().lower() in {"", "null", "none", "n/a", "无"}:
            return None
        return v
