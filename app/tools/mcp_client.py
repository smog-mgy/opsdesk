"""ch08 MCP Client:MultiServerMCPClient 多 Server 接入,现问现拿(每次现拉工具清单,
adapters 每次调用新建 session——Server 侧加工具,服务系统不重启即可见)。
权限/格式化只认我们侧:Server 自报的用途描述仅供模型参考,能不能调按 registry.WRITE_TOOLS。"""
import asyncio
import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import settings
from app.tools import registry
from app.tools.registry import ToolSpec

logger = logging.getLogger(__name__)


def _translate(mapping: dict[str, str], code):
    return mapping.get(code, code)





def _fmt_spare_part(data: dict) -> str:
    """备件库存返回:只挑回答用得到的字段。"""
    if not data.get("found"):
        return f"未找到备件 {data.get('spare_no')}"
    return (f"{data.get('name')}:库存 {data.get('stock')} 件,"
            f"{data.get('eta')},{data.get('status')}")


def _fmt_spare_list(data: dict) -> str:
    """备件清单返回:逐条列关键字段。"""
    items = data.get("items") or []
    if not items:
        return "备件清单为空"
    rows = [f"{it.get('spare_no')} {it.get('name')}:库存 {it.get('stock')} 件,{it.get('eta')},{it.get('status')}"
            for it in items]
    return "；".join(rows)


def _fmt_ticket_ops(data: dict) -> str:
    """工单流转返回:节点/处理人/预计完成。"""
    if not data.get("found"):
        return f"未找到工单 {data.get('ticket_id')}"
    return (f"工单 {data.get('ticket_id')} 当前{data.get('node')},"
            f"处理人 {data.get('assignee')},预计 {data.get('eta')}")


# 结果格式化我们侧登记(挑回答用得上的字段 + 内部枚举码翻人话);未登记的 MCP 工具透传
FORMATTERS: dict = {
    "query_spare_part": _fmt_spare_part,
    "query_spare_list": _fmt_spare_list,
    "query_ticket_progress": _fmt_ticket_ops,
}

_client: MultiServerMCPClient | None = None


def _connections() -> dict:
    """运维版 MCP:备件库存(:8101) + 工单流转(:8102),独立进程。"""
    return {
        "spare_part": {"transport": "streamable_http", "url": settings.mcp_spare_url},
        "ticket_ops": {"transport": "streamable_http", "url": settings.mcp_ticket_url},
    }


def get_client() -> MultiServerMCPClient:
    global _client
    if _client is None:
        # handle_tool_errors=False:工具错误抛 ToolException,由执行引擎统一分诊/回灌
        _client = MultiServerMCPClient(_connections(), handle_tool_errors=False)
    return _client


async def _get_tools_of(*, server_name: str):
    """薄壳:单测 monkeypatch 锚点。"""
    return await get_client().get_tools(server_name=server_name)


async def fetch_mcp_specs() -> list[ToolSpec]:
    specs: list[ToolSpec] = []
    for server in _connections():
        try:
            # 我们侧超时封顶:连接拒绝会快速失败,但 Server 假死(TCP 接了不回话)只受 adapters
            # 默认超时保护——现问现拿每步都拉清单,最坏延迟必须封住
            tools = await asyncio.wait_for(_get_tools_of(server_name=server),
                                           timeout=settings.mcp_tool_timeout)
        except Exception as e:  # noqa: BLE001 单台不可达/假死:告警+跳过,不拖垮本轮对话
            logger.warning("MCP Server「%s」不可达,本轮跳过其工具:%s", server, type(e).__name__)
            continue
        for t in tools:
            specs.append(registry.spec_from_langchain_tool(
                t, source="mcp", mcp_server=server, format_result=FORMATTERS.get(t.name)))
    return specs
