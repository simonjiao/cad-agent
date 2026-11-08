# AutoCAD 2019 + Windows 11 + WSL2 + Codex：MCP 集成与验收包

**目标**：Codex 保留在 WSL2；AutoCAD 2019 保留在 Windows；使用 Windows Python 运行 U-C4N/Autocad-MCP v1.8.0（COM 引擎），通过 stdio + WSL Interop 通信。第一次使用默认只读，写入只在隔离的示例 DWG 中进行。

**版本固定**：`autocad-mcp-pro[com]==1.8.0`；Python 3.11 x64；AutoCAD 完整版 2019（不是 LT）；Windows 11 + WSL2；已经能运行的 Codex CLI。无需自行训练模型。

> 状态说明：已核对官方 AutoCAD ProgID、U-C4N v1.8.0 发布页/代码入口/配置环境变量、微软 WSL 互操作、Codex MCP TOML 配置，并在当前环境完成 Python 静态检查和模拟 stdio 握手。**无法在本环境运行你的 Windows AutoCAD 2019，所以实际 COM、WSL→Windows 与 DWG 验收仍须在你的电脑上执行**。本包不会谎称这些实机测试已通过。

## 1. 先解压到准确目录

把 ZIP 解压后，将**本文件所在目录内全部文件**放到：

`C:\cad-mcp-2019\`

要求：`C:\cad-mcp-2019\windows\install.ps1`、`C:\cad-mcp-2019\wsl\launch_mcp.sh` 存在。**不要多出一层 ZIP 同名目录。**

建议直接在 Windows 本机执行以下步骤，不需要管理员权限；不要把已存在的生产图纸放在此工作区。

## 2. Windows 安装（PowerShell）

前提：安装好 Windows 版 Python **3.11 x64**，并可执行 `py -3.11 --version`。Windows AutoCAD 2019 已能正常启动（完整版，支持 COM），Python 环境连接 PyPI。

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
& 'C:\cad-mcp-2019\windows\install.ps1'
```

安装器在 `C:\cad-mcp-2019\.venv` 创建虚拟环境，下载固定版本 MCP 和 `pywin32`，执行 `pip check` 与入口导入检查；创建 `work\`；将 `mode.txt` 设为 `readonly`。**不会更改 Codex 已有配置**。依赖从 PyPI 下载，不会静默升级到下一版 MCP。

## 3. Windows COM 验证（必须先通过）

1. 手工启动 **AutoCAD 2019 完整版**，让窗口保持打开；打开任何一张无需保存的测试 DWG（也可创建空白图）。
2. 在同一个 Windows 用户下执行：

```powershell
& 'C:\cad-mcp-2019\.venv\Scripts\python.exe' 'C:\cad-mcp-2019\windows\verify_com.py'
```

**通过标准**：输出 `ok:true`、`version` 以 `23.0` 开头、当前文件名和模型空间图元数量。失败时先处理 COM 注册、AutoCAD 运行状态、权限级别等问题；**不应进入写入测试**。

> AutoCAD 2019 为 `AutoCAD.Application.23.0`；若同时装了 2020，仅用 `AutoCAD.Application.23` 会引起版本混淆。脚本强制检查 23.0。

## 4. WSL2 注册 MCP 到 Codex

在 WSL2 终端执行（Windows 安装完成后）：

```bash
cd /mnt/c/cad-mcp-2019
bash wsl/configure_codex.sh          # 先仅生成/显示配置片段
bash wsl/configure_codex.sh --apply  # 备份并追加到 ~/.codex/config.toml
```

生成的片段参考：

```toml
[mcp_servers.autocad2019]
command = "/bin/bash"
args = ["/mnt/c/cad-mcp-2019/wsl/launch_mcp.sh"]
startup_timeout_sec = 60
tool_timeout_sec = 120
supports_parallel_tool_calls = false
```

启动链路是 `Codex(WSL2) → launch_mcp.sh → Windows .venv/Scripts/python.exe → bridge.py → server.main → COM → AutoCAD 2019`。`launch_mcp.sh` 会将当前目录切换到 Windows C: 文件系统，并使用 `wslpath` 将桥接脚本转换为 Windows 路径。

重新启动 Codex，执行：

```bash
codex mcp list
```

**注意**：`codex mcp list` 仅表示配置存在，**不代表 COM 已连通**，还必须执行下一步协议探测。

## 5. WSL2 → Windows MCP 协议验证

AutoCAD 2019 保持打开，PowerShell 不要和 CAD 交互。WSL2 中执行：

```bash
cd /mnt/c/cad-mcp-2019
python3 wsl/probe_mcp.py --mock   # 不依赖 AutoCAD；本地握手自检
python3 wsl/probe_mcp.py --real   # 实际启动 Windows MCP；只调用读取工具
```

`--real` 成功标准：返回 `ok:true`、`tools` 含 `drawing_info`、`drawing_info` 不报错；协议往返经过 Windows Python。失败时会输出错误信息，不会假装成功。

接着在 Codex 会话中复制 `examples/01_readonly_prompt.txt` 的内容发送给 Codex。此时 `mode.txt` 还是 `readonly`；MCP 端的 `READ_ONLY=true` 应拒绝写操作。

## 6. 创建独立 DWG 测试数据

退出当前 Codex 会话，确认 AutoCAD 中没有打开旧的 `ai_demo_baseline.dwg` / `ai_demo_working.dwg`。在 Windows PowerShell 执行：

```powershell
& 'C:\cad-mcp-2019\.venv\Scripts\python.exe' 'C:\cad-mcp-2019\windows\create_demo.py'
```

程序使用真实 AutoCAD COM 创建 `work\ai_demo_baseline.dwg`，包含 100×60 边框四条直线，以及中心 `(50,30)` 半径 10 的圆，总计 5 个模型空间图元；复制为 `work\ai_demo_working.dwg` 并在 AutoCAD 中将该副本设为活动文档；保留 baseline 的 SHA-256 校验值。**程序默认拒绝覆盖旧测试文件**。

若需要从头重做，并且已经关闭 AutoCAD 中的示例图纸：

```powershell
& 'C:\cad-mcp-2019\.venv\Scripts\python.exe' 'C:\cad-mcp-2019\windows\create_demo.py' --reset
```

## 7. 进入仅限测试图纸的可写模式

Windows PowerShell：

```powershell
& 'C:\cad-mcp-2019\windows\set_mode.ps1' -Mode sandbox
```

**重要：** 请仅保留 `ai_demo_working.dwg` 作为 AutoCAD 当前活动图纸；避免在 Agent 执行期间切换图纸标签。桥接器在 MCP **启动时**检查活动文档是否正是这个副本，否则拒绝启动可写 MCP。该检查不是持续锁定，用户之后手工切换标签仍有风险，因此不要同时打开重要工程图纸。

完全退出并重新启动 Codex，复制 `examples/02_edit_prompt.txt` 内容。Agent 应创建 `AI_ADDED` 图层（颜色 3）、一条 `(0,30)→(100,30)` 的线和一个中心 `(50,30)` 半径 15 的圆，保存 working DWG。

## 8. 真正的 DWG 验收（不要只相信 Agent 的回答）

Agent 完成后，在 Windows PowerShell 执行：

```powershell
& 'C:\cad-mcp-2019\.venv\Scripts\python.exe' 'C:\cad-mcp-2019\windows\verify_demo.py' --reopen
```

这一步将要求图纸**已经保存**，关闭并重新打开测试副本，然后通过 AutoCAD COM 重新读取每个图元，核对：

| 验收项 | 期望 |
|---|---|
| AutoCAD 版本 | 23.0（2019） |
| 活动图纸 | `work\ai_demo_working.dwg` |
| AI_BASE 图层 | 原有四条边线 + 半径 10 圆；坐标无变化 |
| AI_ADDED 图层 | 1 LINE + 1 CIRCLE |
| 新直线 | (0,30,0) → (100,30,0) |
| 新圆 | (50,30,0)，半径 15 |
| 模型空间图元数 | 7 |
| baseline 文件 | SHA-256 与初始一致 |
| DWG 保存后重开 | 无报错，图元精确匹配 |

只有 `verify_demo.py --reopen` 退出码 0 并输出 `ok:true`，才能算完成本次 CAD 操作验收。

## 9. 测试完恢复只读

```powershell
& 'C:\cad-mcp-2019\windows\set_mode.ps1' -Mode readonly
```

完全退出并重新打开 Codex。所有写操作再次由 MCP 的只读策略阻止。

## 安全边界和注意事项

- **无在线“AI 控制 CAD”云端服务**：所有 COM 调用走本地 Windows 已安装的 AutoCAD；LLM/Agent 的请求内容仍遵循 Codex 本身的网络、数据和隐私配置。
- MCP 的 `ALLOWED_PATHS` 主要限制文件路径工具，**不是对 AutoCAD 当前活动文档的完整沙箱**；本包另设启动时活动文件校验、只读默认值、禁用裸命令/LISP、禁止通过 MCP 打开/切换/关闭其他文档、禁止破坏级操作。不要把工程 DWG 暴露在可写测试会话中。
- `CAD_LAUNCH=never`，MCP 不会偷偷启动或切换 AutoCAD 版本。`AUTOCAD_MCP_BACKEND=com`，连接失败不会悄悄退化为 DXF 引擎。
- 当前脚本要求 WSL2 挂载 `C:` 到 `/mnt/c/`（微软默认），安装目录固定 `C:\cad-mcp-2019`。如你修改过 WSL automount root，需改 `wsl` 启动脚本中的映射路径。
- `DISCOVERY_MODE=search` 仅展示少量发现工具。Agent 需要调用 `search_tools` → `describe_tool` / `call_tool`。工具说明为动态，若对应 v1.8.0 的工具不可用，必须如实停止。
- Windows COM 桌面应用不是可靠的多 Agent 并行服务器：本包明确 `supports_parallel_tool_calls=false`。不要同时运行多个 Codex/Claude Code 来修改同一 CAD 会话。
- 你的 AutoCAD 2019 可能安装了行业插件或被 IT 策略限制 COM；本包**不保证**在这种环境下直接通过，验收用于发现差异。

## 文件说明

```text
C:\cad-mcp-2019\
  README.md                        这份使用说明
  SOURCES.md                       依据、证据范围
  windows\
    install.ps1                    安装固定版本 Windows MCP
    bridge.py                     COM 版本/权限/当前 DWG 启动保护、stdio 入口
    check_install.py              Windows 解释器/精确包版本/入口验证
    com_common.py                 COM 辅助函数
    verify_com.py                 T1 COM 只读验证
    create_demo.py                T3 创建 5 图元测试 DWG + 工作副本
    verify_demo.py                T5 保存重开、7 图元精确检查
    set_mode.ps1                  readonly / sandbox 模式切换
  wsl\
    launch_mcp.sh                 WSL → Windows MCP 桥接
    configure_codex.sh            生成并注册 Codex MCP 配置
    probe_mcp.py                  T2 MCP 协议握手 + drawing_info 只读调用
    mock_mcp_server.py            仅供离线测试的假服务，非 CAD
  examples\
    01_readonly_prompt.txt        Codex 只读测试提示词
    02_edit_prompt.txt            Codex 修改与校验示例
  tests\
    test_offline.py                不需要 Windows 的结构/协议测试
```

## 故障定位（按实际报错处理）

| 现象 | 优先核查 |
|---|---|
| Windows `GetActiveObject` 失败 | AutoCAD 2019 已启动、完整版、同一 Windows 用户/权限级别、COM 注册状态 |
| 连接成 2020/其他版本 | `CAD_PROGID=AutoCAD.Application.23.0`、Windows COM 注册、COM 验证脚本输出 |
| `python3 wsl/probe_mcp.py --real` 超时 | WSL Interop 是否允许、Windows Python.exe 能否启动、MCP startup 错误、CAD UI 是否阻塞 |
| MCP 成功但没法修改 | 当前 `mode.txt` 是否仍 `readonly`；修改后是否完全重启 Codex |
| `sandbox` 启动失败 | 2019 运行中，活动文档必须为 `work\ai_demo_working.dwg` |
| 模型有响应但图元不符合 | 核查新增图层/坐标；以 `verify_demo.py --reopen` 为准，不以自然语言“成功”为准 |
| `codex mcp list` 有条目但工具不可用 | 继续跑 `probe_mcp.py --real`，明确是否属于 stdio/COM/生命周期错误 |

## 本包静态测试命令（不需要 AutoCAD）

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 wsl/probe_mcp.py --mock
```

工具依赖和版本均留有明确来源，见 `SOURCES.md`。
