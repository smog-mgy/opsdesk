import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.extract import TicketExtract, ExtractRequest, RequestType


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(session_id="s1", message="")


def test_extract_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        ExtractRequest(text="")


def test_ticket_ticket_id_nullable():
    t = TicketExtract(ticket_id=None, request_type="报修", expected_solution="更换备件")
    assert t.ticket_id is None
    assert t.request_type is RequestType.REPORT


def test_ticket_rejects_unknown_request_type():
    with pytest.raises(ValidationError):
        TicketExtract(ticket_id=None, request_type="砍价", expected_solution="x")


def test_ticket_normalizes_placeholder_ticket_id_to_none():
    for placeholder in ("null", "None", "无", " N/A ", ""):
        t = TicketExtract(
            ticket_id=placeholder, request_type="投诉", expected_solution="x"
        )
        assert t.ticket_id is None, placeholder
    assert TicketExtract(
        ticket_id="MH20260701123", request_type="报修", expected_solution="x"
    ).ticket_id == "MH20260701123"
