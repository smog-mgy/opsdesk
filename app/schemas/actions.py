from typing import Literal

from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    conversation_id: int
    description: str = Field(min_length=1)
    ticket_type: Literal["报修", "投诉", "咨询"]


class CreateTicketResponse(BaseModel):
    ticket_no: str
    status: str = "已转人工"


class ConfirmTicketRequest(BaseModel):
    conversation_id: int
    ticket_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ResumeRequest(BaseModel):
    conversation_id: int
    ticket_id: str | None = Field(default=None, min_length=1)   # ch06 工单选择器点选
    confirmed: bool | None = None                              # ch08 工单预览 确认/取消
