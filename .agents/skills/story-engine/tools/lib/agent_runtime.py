"""Agent Runtime：支持 tool calling 的多轮对话循环（内部工具，不是外部 agent 模式）。

⚠️ 注意：这不是"agent 模式"。真正的 agent 模式由 opencode agent （LLM）直接执行，不走 Python 调 API。
这个 Runtime 是供 API 模式内部使用的简单 tool calling 工具，不是外部 agent 模式的实现。

设计原则：
- 与现有 API 模式完全兼容，零侵入
- Runtime 只做循环+工具调度，不关心业务逻辑
- 工具由调用方注册，可复用现有 Python 函数
- 错误恢复：工具异常 → 回传 LLM 自行决策

用法：
    rt = AgentRuntime(api_key, model, system_prompt)
    rt.register_tool("read_file", fn, schema)
    result = rt.run(user_prompt, max_turns=15)
"""

import json
import time
from typing import Any, Callable

from lib.api_client import DEFAULT_API_URL


class AgentRuntime:
    """多轮 Agent 循环，支持 tool calling。"""

    def __init__(self, api_key: str, model: str,
                 system_prompt: str = "",
                 api_url: str = None,
                 temperature: float = 0.8,
                 max_tokens: int = 8192,
                 verbose: bool = True):
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.api_url = api_url or DEFAULT_API_URL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.verbose = verbose

        self._tools: list[dict] = []
        self._tool_map: dict[str, Callable] = {}
        self._messages: list[dict] = []
        self._turn = 0

    def register_tool(self, name: str, fn: Callable,
                      description: str = "",
                      parameters: dict = None):
        """注册一个工具。

        Args:
            name: 工具名（LLM 调用时使用）
            fn: 执行函数，接收 **kwargs
            description: 工具描述
            parameters: JSON Schema 格式的参数定义
        """
        self._tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters or {"type": "object", "properties": {}}
            }
        })
        self._tool_map[name] = fn

    def register_tools(self, tool_defs: list[dict]):
        """批量注册工具。

        tool_defs: [{"name": fn, "description": ..., "parameters": ...}, ...]
        """
        for td in tool_defs:
            self.register_tool(
                td["name"], td["fn"],
                description=td.get("description", ""),
                parameters=td.get("parameters")
            )

    def run(self, user_prompt: str, max_turns: int = 15,
            context_limit: int = 64000) -> str:
        """执行 Agent 循环。

        Args:
            user_prompt: 用户输入的初始 prompt
            max_turns: 最大工具调用轮数
            context_limit: context 字符数限制（超限时截断最早 tool 结果）

        Returns:
            LLM 最终回复文本
        """
        if not self._tools:
            raise ValueError("AgentRuntime: 未注册任何工具")

        self._messages = [{"role": "system", "content": self.system_prompt}]
        self._messages.append({"role": "user", "content": user_prompt})
        self._turn = 0

        while self._turn < max_turns:
            self._turn += 1
            self._log(f"[Turn {self._turn}/{max_turns}] 调用 LLM...")

            response = self._call_api()
            if response is None:
                return self._last_content()

            assistant_msg = response["message"]
            self._messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # LLM 直接返回文本 → 任务完成
                content = assistant_msg.get("content", "")
                self._log(f"[Turn {self._turn}] ✓ 完成 ({len(content)} chars)")
                return content

            # 执行工具调用
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                fn = self._tool_map.get(tool_name)
                if fn is None:
                    result = f"错误：未知工具 '{tool_name}'"
                else:
                    try:
                        t0 = time.time()
                        result = fn(**args)
                        elapsed = time.time() - t0
                        result_str = str(result)
                        if len(result_str) > 5000:
                            result_str = result_str[:5000] + f"\n...（截断，总长 {len(result_str)} chars）"
                        self._log(f"  -> {tool_name}({json.dumps(args, ensure_ascii=False)[:100]}) = {result_str[:100]} ({elapsed:.1f}s)")
                        result = result_str
                    except Exception as e:
                        result = f"工具执行异常: {type(e).__name__}: {e}"
                        self._log(f"  ! {tool_name} 异常: {e}")

                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })

            # context 超限保护：截断最早的 tool 消息对
            self._trim_context(context_limit)

        # 达 max_turns，返回最后一条 LLM 回复
        self._log(f"[Max Turns] 达上限 {max_turns}，返回最后回复")
        return self._last_content()

    def _call_api(self) -> dict | None:
        """调用 LLM API，返回响应 JSON。"""
        import requests

        data = {
            "model": self.model,
            "messages": self._messages,
            "tools": self._tools,
            "tool_choice": "auto",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=180,
            )
            if resp.status_code != 200:
                self._log(f"  [API Error] {resp.status_code}: {resp.text[:200]}")
                return None
            return resp.json()["choices"][0]
        except requests.exceptions.Timeout:
            self._log("  [API Timeout]")
            return None
        except Exception as e:
            self._log(f"  [API Error] {e}")
            return None

    def _trim_context(self, limit: int):
        """当消息总长超限时，保留 system+user，删除最旧的 tool 来回对。"""
        total = sum(len(json.dumps(m, ensure_ascii=False)) for m in self._messages)
        if total <= limit:
            return

        self._log(f"  [Trim] context {total} > {limit}，压缩中...")
        # 找到第一个 tool 消息的索引
        keep = []
        # 保留 system + 第一条 user
        keep.append(self._messages[0])  # system
        keep.append(self._messages[1])  # user

        # 从最新的往前保留
        tail = []
        for m in reversed(self._messages[2:]):
            tail.insert(0, m)
            if sum(len(json.dumps(m2, ensure_ascii=False)) for m2 in keep + tail) <= limit:
                continue
            break

        self._messages = keep + tail
        # 追加提示
        self._messages.insert(len(self._messages),
            {"role": "user", "content": "（因 context 限制，中间 tool 调用已省略。请继续。）"})

    def _last_content(self) -> str:
        """返回最后一条 assistant 消息的内容。"""
        for m in reversed(self._messages):
            if m["role"] == "assistant" and m.get("content"):
                return m["content"]
        return ""

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [Agent] {msg}", flush=True)

    @property
    def turn_count(self) -> int:
        return self._turn

    def get_messages(self) -> list[dict]:
        return list(self._messages)
