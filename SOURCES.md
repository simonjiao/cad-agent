# 证据与限制（2026-11-08 核对）

## 官方/源代码依据

1. U-C4N/Autocad-MCP GitHub：https://github.com/U-C4N/Autocad-MCP
2. U-C4N v1.8.0 release：https://github.com/U-C4N/Autocad-MCP/releases/tag/v1.8.0
   - 2026-11-06 发布；官方声明新增完整可回溯操作日志、发现模式、工具策略等。
3. U-C4N pyproject.toml：https://github.com/U-C4N/Autocad-MCP/blob/v1.8.0/pyproject.toml
   - Python >=3.11；PyPI 名称 autocad-mcp-pro；`[com]` 额外依赖 pywin32/Pillow；入口 `autocad-mcp = "server:main"`。
4. U-C4N server.py：https://github.com/U-C4N/Autocad-MCP/blob/v1.8.0/server.py
   - main() stdio 入口；`AUTOCAD_MCP_BACKEND=com` 失败时不退化到 ezdxf；`drawing_info` 等工具。
5. U-C4N config.py：https://github.com/U-C4N/Autocad-MCP/blob/v1.8.0/config.py
   - `CAD_PROGID`, `CAD_LAUNCH`, `ALLOWED_PATHS`, `READ_ONLY`, `MAX_TOOL_COST`, `TOOL_DENYLIST`, `DISCOVERY_MODE`。
6. Autodesk 官方 COM ProgID：https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-ActiveX-CAO/files/GUID-0EDC04D5-2ACB-4555-B5AC-936D54A9FF61.htm
   - AutoCAD 2019 为 `AutoCAD.Application.23.0`；2020 为 `.23.1`。
7. 微软 WSL Interop：https://learn.microsoft.com/en-us/windows/dev-environment/wsl-interop
   - WSL shell 可启动 Windows `.exe`，支持 stdin/stdout 互操作。
8. Codex MCP 配置文档：https://learn.chatgpt.com/docs/extend/mcp?surface=cli
9. Codex Config Reference：https://learn.chatgpt.com/docs/config-file/config-reference
   - `mcp_servers.<id>.command/args/startup_timeout_sec/tool_timeout_sec` 等。

## 证据级别

- **已由官方文档确认**：AutoCAD 2019 COM ProgID；WSL 调用 Windows 可执行文件的原理；Codex 的 MCP 配置形式。
- **已由 U-C4N 代码与 Release 记录确认**：MCP v1.8.0 依赖、stdio 入口、参数、COM 路线、只读及工具权限。
- **作者报告，未独立实测**：仓库所述真实 AutoCAD 2026 测试覆盖与工程有效性。不能推广成 AutoCAD 2019 已通过。
- **本包已执行的环境无关测试**：Python 语法检查、离线 unittest、模拟 MCP stdio 握手。由于当前容器无 Windows/AutoCAD，不声称完成 2019 实机验证。

## 三项剩余风险

1. AutoCAD 2019 的 COM 在特定补丁/权限/插件环境中的兼容性必须用 `verify_com.py` 和工作副本实测。
2. MCP `ALLOWED_PATHS` 只保护经过路径校验的操作；对已经打开的活动 DWG 没有操作系统级隔离。`bridge.py` 的 sandbox 文档路径校验只在**启动时**执行。
3. Codex/WSL2/Windows 的 stdio 互操作需要在用户环境中做 MCP 握手测试。当前不能外推 Linux mock 的成功等于 Windows 真机通过。
