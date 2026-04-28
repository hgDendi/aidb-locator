# aidb-locator UI · 设计文档

> Date: 2026-04-28
> Source: Brainstorming session
> Scope: aidb-locator (子项目 `aidb_locator.ui`)
> Category: design

## 背景（Context）

字节的 [CodeLocator](https://github.com/bytedance/CodeLocator) 原本是 Android Studio 插件，依赖 IDE 才能使用。本仓库已经把它的 ADB 协议剥离出来，做成了 Python 库 + CLI + MCP server（`aidb_locator`），但仍然没有图形界面，非开发者或不想开 AS 的同事仍然无法直接使用。

本设计在不改动现有 `aidb_locator` 核心库的前提下，新增一个**本地 Web GUI 子项目**，把"截图 + 点击拉布局 + 属性编辑"等核心调试能力做成浏览器界面，安装即用。

## 目标与非目标

### 目标
1. **核心**：导出设备截图 → 浏览器可视化 → 鼠标点击截图能拉出对应 view 的布局信息
2. **零打包负担**：通过 `pip install` 分发，无需 DMG / 公证 / Electron
3. **薄包装**：UI 只是 `aidb_locator.commands` 的 HTTP 层 + 前端，不重复业务逻辑

### 非目标（明确不做）
- 在截图上模拟点击触发设备事件（A2，留给 v2）
- 历史快照管理（C1，留给 v2）
- 文件浏览器（D2）
- 暗色模式 / 主题（D3）
- WebSocket 实时推送（手动刷新已够用）
- 用户登录 / 多租户 / 远程部署（本地工具）

## 技术栈

| 层 | 选择 | 理由 |
|----|------|------|
| 后端 | FastAPI + uvicorn | 与 `aidb_locator.commands` 直接 import，无 IPC |
| 前端 | 原生 HTML + Vue 3 (CDN) + Tailwind (CDN) | 零构建步骤；交互复杂度刚好需要响应式框架 |
| 设备截图 | 新增 `commands.screenshot()`，调用 `adb exec-out screencap -p` | 现有 `capture` 只能拍单个 view |
| 点击拉布局 | 前端用缓存的 layout 树本地查找（坐标命中最深叶子） | 比 `adb touch` round-trip 快；离线也能玩 |

## 仓库结构与发布

新增子包 `src/aidb_locator/ui/`，结构：

```
src/aidb_locator/ui/
  __init__.py
  server.py           # FastAPI app + uvicorn 启动 + main() 入口
  api/
    __init__.py
    devices.py        # GET /api/devices
    layout.py         # GET /api/snapshot, /api/layout, /api/screenshot, /api/activity
    edit.py           # POST /api/edit, /api/schema, /api/touch
    capture.py        # GET /api/capture/{view_addr}
  static/
    index.html
    app.js            # Vue 3 应用
    style.css
```

`pyproject.toml` 增加 console script：

```toml
[project.scripts]
aidb     = "aidb_locator.cli:main"          # 已有
aidb-ui  = "aidb_locator.ui.server:main"    # 新增
```

用户使用：

```bash
pip3 install git+https://github.com/hgDendi/aidb-locator.git
aidb-ui                    # 启动后自动打开浏览器到 http://127.0.0.1:<port>
aidb-ui --port 8765        # 指定端口
aidb-ui --no-browser       # 只起服务不开浏览器
aidb-ui --host 0.0.0.0     # 局域网共享（可选）
```

默认端口策略：先尝试 8765，被占用则向上递增找到第一个空闲端口。

## 架构

```
┌─────────────────────────────────────────────────────┐
│  浏览器（Vue 3 SPA）                                 │
│  - canvas 渲染截图 + 高亮框                          │
│  - 树视图 + 搜索过滤                                 │
│  - 属性编辑表单                                      │
│  - 本地 findViewAt(tree, x, y) 算法                  │
└────────────────┬────────────────────────────────────┘
                 │ HTTP (JSON / PNG)
┌────────────────▼────────────────────────────────────┐
│  FastAPI (uvicorn, 单进程)                           │
│  - /api/* 端点（薄包装）                             │
│  - StaticFiles mount → static/                       │
└────────────────┬────────────────────────────────────┘
                 │ 直接 import
┌────────────────▼────────────────────────────────────┐
│  aidb_locator.commands  (现有库，零修改 + 一个新增)  │
│  - dump_layout / dump_activity / capture / edit ...  │
│  - **新增** screenshot()  ← 调 adb exec-out screencap│
└────────────────┬────────────────────────────────────┘
                 │
              ADB / 设备
```

**关键设计原则**：
- **后端薄**：每个 API 都是 `commands.xxx()` 的 HTTP 包装
- **快照模型**：截图 + layout + activity 作为一次"快照"绑定，前端缓存；用户点刷新才重新拉。中间所有点击 / hover / 选中都基于这份快照，不打 ADB
- **无服务端 session**：服务器无状态，所有 query 接受 `?device=<serial>`，无参用第一个设备
- **单进程足够**：本地工具，并发 1 个用户

## UI 布局

三栏 + 顶栏 + 底栏：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [设备▼: emulator-5554]  Activity: HomeActivity              [🔄 刷新]        │
│                         Fragments: HomeFragment > FeedFragment              │
├─────────────────┬──────────────────────────────────┬────────────────────────┤
│ 🔍 搜索 view…   │                                  │  选中节点元信息        │
│                 │                                  │  class / id / bounds   │
│ ▾ DecorView     │      [设备截图 canvas]           │  text                  │
│   ▾ LinearLayout│                                  │  [📋 复制 id/路径/坐标]│
│     ▸ Toolbar   │   悬停: 红虚框 + tooltip         │  ─────                 │
│     ▾ FrameLay  │   点击: 蓝实框选中               │  ▾ 编辑属性             │
│       • TextView│                                  │   按 EditType 分组表单 │
│       • Image   │                                  │   [💾 应用到设备]       │
│     ▸ BottomNav │                                  │  ─────                 │
│  (按搜索过滤)   │                                  │  [📥 导出该 view 截图] │
├─────────────────┴──────────────────────────────────┴────────────────────────┤
│ Schema: [_____________________________] [🚀 跳转]   [📥 导出 layout JSON]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 各栏职责

| 区域 | 元素 | 行为 |
|------|------|------|
| 顶栏 | 设备下拉 (D1) | 切换后自动刷新一次快照 |
| 顶栏 | Activity / Fragment 标题 (B2) | 来自 `dump_activity` |
| 顶栏 | 🔄 刷新按钮 (A4) | 并发拉 screenshot + layout + activity，重置整个快照 |
| 左栏 | 搜索框 (A3) | 按 id / class / text 子串过滤；命中节点自动展开父链 |
| 左栏 | 树视图 | 点击节点 → 高亮 + 同步右栏 |
| 中栏 | canvas 截图 | hover 红虚框 (A1) / click 蓝实框 |
| 右栏 | 元信息块 | 显示 class/id/bounds/text，复制按钮 (B4) |
| 右栏 | 编辑表单 (B1) | 按 EditType 自动选控件 |
| 右栏 | 导出 view 截图 (C3) | 调 `/api/capture/{view_addr}` 下载 PNG |
| 底栏 | Schema 输入 (B3) | 调 `/api/schema` |
| 底栏 | 导出 layout JSON (C2) | 直接前端把缓存的树 JSON 下载 |

### 编辑表单的控件映射

| EditType 代码 | 含义 | 前端控件 |
|---|---|---|
| `T` | 文字 | text input |
| `P` / `M` | Padding / Margin | 4 个 number input（left/top/right/bottom） |
| `A` | 透明度 | slider 0-1，步长 0.01 |
| `B` / `TC` | 背景 / 文字色 | `<input type="color">` |
| `TS` | 文字大小 | number input |
| `VF` | 可见性 | 下拉 V / I / G |
| `LP` | 宽高 | 2 个 number input |
| `TXY` / `SCXY` | 位移 / 缩放 | 2 个 number input |

提交后**自动刷新一次快照**（重新拉截图 + 树），让用户立即看到效果。

## 核心交互流程

### 1. 启动 / 刷新（A4 手动）
- 用户点 🔄 → 前端并发发起 `GET /api/snapshot?device=X`
- 后端在该端点内并发调用 `screenshot()` / `dump_layout()` / `dump_activity()`，合并返回：
  ```json
  {
    "screenshot_png_b64": "...",
    "layout": { /* 树 JSON */ },
    "activity": { "activity": "...", "fragments": [...] },
    "device_size": { "width": 1080, "height": 2340 }
  }
  ```
- 前端拿到后渲染 canvas + 树 + 顶栏
- 此后所有 hover / click / select 都基于这份缓存，不触发新的 ADB 调用

### 2. 截图点击 → 拉布局（核心）
1. 前端把 canvas 的 `(clickX, clickY)` 反算回设备坐标：`(devX, devY) = (clickX/scale, clickY/scale)`
2. 调 `findViewAt(layoutTree, devX, devY)`：
   - 深度优先遍历，记录所有 bounds 包含该点的节点
   - 返回**最深**的命中节点（叶子优先；同深度取最后一个，按 z-order 模拟）
3. 高亮：canvas 画蓝色实线框，左栏树展开父链 + 滚动到该项 + 高亮，右栏填充属性
4. 兜底：若 `layoutTree` 为空（用户还没拉过快照），调 `POST /api/touch { x, y }` 让设备返回 view 路径，再单独 `GET /api/layout` 补一份

### 3. 悬停高亮（A1）
- canvas `mousemove` 节流到 30fps（`requestAnimationFrame`）
- 复用 `findViewAt`，画**红色虚线框** + 顶部 tooltip 显示 `class@id`
- 鼠标离开 canvas 清除虚框

### 4. 编辑（B1）
- 用户改完表单点「应用到设备」→ `POST /api/edit { device, view_addr, edit_type, value }`
- 后端调 `commands.edit_view(...)`
- 成功 → 前端**自动触发一次刷新**
- 失败 → 右栏顶部红色 banner 显示错误（保留表单内容方便重试）

### 5. 导出
- **C2 layout JSON**：纯前端，把缓存的 `layout` 字段 `JSON.stringify` 后用 `<a download>` 触发下载
- **C3 view 截图**：调 `GET /api/capture/{view_addr}?device=X` → 后端返回 PNG → 前端 `<a download>` 触发下载

## API 详细清单

| 方法 | 路径 | 请求 | 响应 | 用途 |
|------|------|------|------|------|
| GET | `/api/devices` | — | `[{"serial":"...","state":"device"}]` | 列设备 |
| GET | `/api/snapshot?device=` | — | 见上文「快照」结构 | 一次性拉全（首选） |
| GET | `/api/screenshot?device=` | — | `image/png` | 单独取截图 |
| GET | `/api/layout?device=` | — | layout JSON | 单独取树 |
| GET | `/api/activity?device=` | — | `{activity, fragments}` | 单独取 Activity |
| GET | `/api/capture/{view_addr}?device=` | — | `image/png` | 单 view 截图 (C3) |
| POST | `/api/edit` | `{device, view_addr, edit_type, value}` | `{ok: true}` 或错误 | 改属性 (B1) |
| POST | `/api/schema` | `{device, schema}` | `{ok: true}` | Schema 跳转 (B3) |
| POST | `/api/touch` | `{device, x, y}` | `{view_addr, ...}` | 兜底点击 |

## 错误处理

| 场景 | 后端 | 前端 |
|------|------|------|
| 无设备连接 | 409 Conflict + `{error: "no_device"}` | 顶部 banner："未检测到设备，请连接 USB 或启动模拟器" + 「重新检测」按钮 |
| CodeLocator SDK 未集成 | 424 Failed Dependency + `{error: "sdk_missing"}` | banner："目标 app 需要集成 CodeLocator SDK" — 但截图功能仍可用 |
| ADB 命令超时 | 504 Gateway Timeout | banner + 重试按钮 |
| EditType 参数格式错 | 400 + 详细 message | 表单字段下方显示错误 |
| 多设备未指定 | 默认用第一个 | 顶栏明确显示当前 serial |

## 测试策略

### 后端
- pytest + httpx AsyncClient
- mock `aidb_locator.commands` 层，验证 HTTP 层的参数透传、错误码映射、合并 endpoint 的并发逻辑
- 文件位置：`tests/ui/test_api_*.py`

### 前端
- 把核心算法 `findViewAt(tree, x, y)` 抽成纯函数（`static/findViewAt.js`），用 vitest 或 node 自带 `node:test` 跑 unit test，覆盖：
  - 命中嵌套叶子
  - 命中边界
  - 重叠区域取最后绘制
  - 空树 / 越界

### 端到端
- 手动 checklist（写在 `tests/ui/MANUAL.md`）：
  1. 连真机 → `aidb-ui` → 浏览器自动打开
  2. 选设备 → 看到截图 + 树 + Activity
  3. 点击截图任意位置 → 树同步选中 + 蓝框
  4. hover → 红虚框跟随
  5. 搜索框输入 id 关键字 → 树过滤 + 父链展开
  6. 编辑 padding → 应用 → 截图刷新且生效
  7. Schema 跳转 → 设备跳页 + 自动刷新
  8. 导出 layout JSON / view 截图 → 浏览器下载

## 开放风险

1. **大型 view 树**（>1000 节点）的搜索 / 渲染性能：先做基础版，必要时加虚拟滚动
2. **设备截图分辨率高**（2K+）→ canvas 渲染慢：先按容器宽度缩放，必要时降采样
3. **CodeLocator SDK 协议在不同 Android 版本下的兼容性**：现有 `aidb_locator` 已在处理，UI 层不需重复

## 后续可能的 v2
- A2 截图模拟点击 / 长按 / 滑动
- C1 历史快照对比
- D2 文件浏览器
- D3 暗色模式
- 录屏 / 操作回放
