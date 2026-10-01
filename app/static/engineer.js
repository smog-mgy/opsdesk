/* ch11 工程师工单台:列表(分页/状态筛选/关键词)、处理(状态机校验 + 处理人/备注)、
   WebSocket 状态变更实时刷新。API 见 app/api/engineer.py。 */

const STATUS = ["待派单", "处理中", "待配件", "已解决"];
const STATUS_CLS = { "待派单": "s0", "处理中": "s1", "待配件": "s2", "已解决": "s3" };
const PRI_CLS = { "P1": "p1", "P2": "p2", "P3": "p3" };

const state = { page: 1, size: 10, status: "", keyword: "" };
let flow = {};

function pill(txt, cls) {
  const s = el("span", "pill " + (cls || ""));
  s.textContent = txt;
  return s;
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadFlow() {
  try { flow = (await api("/api/engineer/status-flow")).flow; } catch (e) { flow = {}; }
}

function renderTabs() {
  const box = $("statusTabs");
  box.textContent = "";
  const all = el("button", "tab" + (state.status === "" ? " on" : ""), "全部");
  all.onclick = () => { state.status = ""; state.page = 1; load(); renderTabs(); };
  box.appendChild(all);
  for (const s of STATUS) {
    const b = el("button", "tab" + (state.status === s ? " on" : ""), s);
    b.onclick = () => { state.status = s; state.page = 1; load(); renderTabs(); };
    box.appendChild(b);
  }
}

function row(t) {
  const tr = el("tr");
  tr.appendChild(el("td", null, t.ticket_no));
  tr.appendChild(el("td", null, t.ticket_type || "—"));
  tr.appendChild(el("td", null, t.user_id || "—"));
  const desc = el("td", "desc", esc(t.description));
  tr.appendChild(desc);
  const pr = el("td", null, "");
  pr.appendChild(pill(t.priority, PRI_CLS[t.priority] || ""));
  tr.appendChild(pr);
  const st = el("td", null, "");
  st.appendChild(pill(t.status, STATUS_CLS[t.status] || ""));
  tr.appendChild(st);
  tr.appendChild(el("td", null, t.handler || "—"));
  tr.appendChild(el("td", null, t.progress_note || "—"));
  tr.appendChild(el("td", null, fmtTime(t.created_at)));
  tr.appendChild(el("td", null, fmtTime(t.updated_at)));
  const op = el("td", null, "");
  const btn = el("button", "btn", "处理");
  btn.onclick = () => openModal(t);
  op.appendChild(btn);
  tr.appendChild(op);
  return tr;
}

async function load() {
  const qs = new URLSearchParams({ page: state.page, size: state.size });
  if (state.status) qs.set("status", state.status);
  if (state.keyword) qs.set("keyword", state.keyword);
  const box = $("rows");
  try {
    const d = await api("/api/engineer/tickets?" + qs.toString());
    box.textContent = "";
    if (!d.items.length) {
      const tr = el("tr");
      const td = el("td", "miss", "没有匹配的工单");
      td.colSpan = 11;
      tr.appendChild(td);
      box.appendChild(tr);
    } else {
      for (const t of d.items) box.appendChild(row(t));
    }
    renderPager(d.total, d.page, d.size);
  } catch (e) {
    box.textContent = "";
    const tr = el("tr");
    const td = el("td", "miss", "取数失败：" + e.message);
    td.colSpan = 11;
    tr.appendChild(td);
    box.appendChild(tr);
  }
}

function renderPager(total, page, size) {
  const pages = Math.max(1, Math.ceil(total / size));
  const p = $("pager");
  p.textContent = "";
  p.appendChild(el("span", null, "共 " + total + " 条 · 第 " + page + "/" + pages + " 页"));
  const prev = el("button", "btn", "上一页");
  prev.disabled = page <= 1;
  prev.onclick = () => { if (page > 1) { state.page = page - 1; load(); } };
  const next = el("button", "btn", "下一页");
  next.disabled = page >= pages;
  next.onclick = () => { if (page < pages) { state.page = page + 1; load(); } };
  p.appendChild(prev);
  p.appendChild(next);
}

let current = null;

async function openModal(t) {
  current = t;
  $("mNo").textContent = t.ticket_no;
  const dl = $("mDetail");
  dl.textContent = "";
  const kvs = [
    ["报修人", t.user_id || "—"],
    ["类型", t.ticket_type || "—"],
    ["优先级", t.priority || "—"],
    ["当前状态", t.status || "—"],
    ["处理人", t.handler || "—"],
    ["报修时间", fmtTime(t.created_at)],
    ["更新时间", fmtTime(t.updated_at)],
    ["问题描述", esc(t.description)],
  ];
  for (const [k, v] of kvs) {
    dl.appendChild(el("dt", null, k));
    dl.appendChild(el("dd", null, v));
  }
  const sel = $("mStatus");
  sel.textContent = "";
  const targets = (flow[t.status] || []).filter((s) => s !== t.status);
  if (!targets.length) {
    const o = el("option");
    o.value = t.status;
    o.textContent = t.status + "（终态）";
    sel.appendChild(o);
    sel.disabled = true;
    $("mHint").textContent = "当前已是终态，不可再流转。";
  } else {
    sel.disabled = false;
    for (const s of targets) {
      const o = el("option");
      o.value = s;
      o.textContent = s;
      sel.appendChild(o);
    }
    $("mHint").textContent = "合法流转：" + targets.join(" → ") + "（非法跳转会被后端拒绝）";
  }
  $("mHandler").value = t.handler || "";
  $("mNote").value = t.progress_note || "";
  $("mask").classList.add("open");
}

async function save() {
  const body = { status: $("mStatus").value };
  const handler = $("mHandler").value.trim();
  const note = $("mNote").value.trim();
  if (handler && handler !== current.handler) body.handler = handler;
  if (note && note !== current.progress_note) body.progress_note = note;
  try {
    const d = await api("/api/engineer/tickets/" + encodeURIComponent(current.ticket_no), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    toast("工单 " + d.ticket_no + " 已更新为「" + d.status + "」");
    $("mask").classList.remove("open");
    load();
  } catch (e) {
    toast(e.message, true);
  }
}

function setupWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(proto + "://" + location.host + "/api/engineer/ws");
  ws.onopen = () => { $("wsNote").textContent = "实时推送：已连接"; };
  ws.onclose = () => {
    $("wsNote").textContent = "实时推送：已断开（页面操作不受影响，刷新即恢复）";
  };
  ws.onerror = () => { try { ws.close(); } catch (e) { /* ignore */ } };
  ws.onmessage = (ev) => {
    try {
      const m = JSON.parse(ev.data);
      if (m.type === "ticket_updated") {
        toast("工单 " + m.ticket.ticket_no + " 状态更新为「" + m.ticket.status + "」（实时）");
        load();
      }
    } catch (e) { /* ignore */ }
  };
}

$("refreshBtn").addEventListener("click", load);
$("searchBtn").addEventListener("click", () => {
  state.keyword = $("keyword").value.trim();
  state.page = 1;
  load();
});
$("keyword").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    state.keyword = $("keyword").value.trim();
    state.page = 1;
    load();
  }
});
$("mCancel").addEventListener("click", () => $("mask").classList.remove("open"));
$("mSave").addEventListener("click", save);
$("mask").addEventListener("click", (e) => {
  if (e.target === $("mask")) $("mask").classList.remove("open");
});

(async () => {
  await loadFlow();
  renderTabs();
  load();
  setupWS();
})();
