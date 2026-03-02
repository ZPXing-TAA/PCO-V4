# Auto_Scripts_v4（先映射，再微调）

## 设计原则

本版本遵循固定流程：

1. 先做分辨率映射（Mapping）
2. 再做偏置微调（Offset）

基准文件有两个，地位相同：

- 动作基准：`actions/global_actions.py`
- 分辨率基准：`mapping/huaweipura.py`

其他设备一律基于这两个基准计算，不再复制整份动作实现。

## 目录说明

- `actions/global_actions.py`：统一动作实现与映射逻辑
- `mapping/*.py`：每台设备一个分辨率文件（仅 `WIDTH/HEIGHT`）
- `actions/actions_*.py`：每台设备一个入口文件（选择 mapping + 可选 offsets）
- `config/switcher.py`：渲染配置应用入口（按设备分辨率自动映射 tap/swipe 坐标）

## 现有设备文件

- `mapping/huaweipura.py`
- `mapping/huaweimate.py`
- `mapping/oppo_findx9pro.py`
- `actions/actions_huaweipura.py`
- `actions/actions_huaweimate.py`
- `actions/actions_oppo.py`

当前设备文件里的 `OFFSETS` 默认都是 `{}`，即只做映射不做微调。

## 新增设备详细步骤

1. 新建分辨率文件
   - 复制 `mapping/device_template.py`
   - 重命名为 `mapping/<device>.py`
   - 填入真实分辨率：

```python
WIDTH = 0
HEIGHT = 0
```

2. 新建设备动作入口
   - 复制 `actions/actions_device_template.py`
   - 重命名为 `actions/actions_<device>.py`
   - 设置：

```python
MAPPING_MODULE = "mapping.<device>"
OFFSETS = {}
bind_actions(globals(), mapping_module=MAPPING_MODULE, offsets=OFFSETS)
```

3. 在测试/录制脚本中切换模块
   - 把脚本里的 `GLOBAL_ACTIONS_MODULE` 改成：

```python
os.environ["GLOBAL_ACTIONS_MODULE"] = "actions.actions_<device>"
```

4. 先跑映射结果（不加偏置）
   - 保持 `OFFSETS = {}`
   - 先验证大多数动作是否可用

5. 再做少量微调
   - 仅对偏差动作添加 key，不需要全量配置
   - 示例：

```python
OFFSETS = {
    "MOVE": (0, 0),
    "ATTACK": (0, 0),
    "TURN_180_R": (0, 0),
}
```

## Offset 生效顺序

最终坐标 = 映射后的坐标 + `GLOBAL` + `GROUP` + `POINT`

- `GLOBAL`：全局偏移
- `GROUP`：动作组偏移（如 `MOVE` / `TURN` / `ATTACK`）
- `POINT`：单个点位偏移（如 `MOVE_START` / `TURN_180_R`）

## Render Config 映射规则

- 基准渲染配置目录：`/Users/xingzhengpeng/CODEZONE/PCO/Power-Optimization/render_configs`
- 该目录视为 `huaweipura` 基准坐标。
- 调用 `apply_render_config(json_path)` 时，会自动读取当前 `GLOBAL_ACTIONS_MODULE` 对应的
  `BASE_RESOLUTION/TARGET_RESOLUTION`，将 json 中 `tap/swipe` 坐标按分辨率比例映射到当前设备。
- 因此同一份基准 `render_configs` 可复用于所有设备；只有个别不准时再通过设备 `OFFSETS` 微调动作。

## 兼容性说明（与原 routes）

- 路线文件（`routes/*`）不需要改。
- `engine/runner.py` 的调用方式不变，仍通过 `GLOBAL_ACTIONS_MODULE` 动态加载动作模块。
- 只要脚本正确指向 `actions.actions_<device>`，原有 route 的动作名可以按原流程执行。

注意：兼容性指“执行链路不破坏”。动作落点精度取决于分辨率是否正确、以及后续是否需要补少量 `OFFSETS`。


## Multi-route 全局计数回档

当你发现某条 route 的录制从某个 `record_start` 开始错位时，不需要再手动逐个动作改 `_action_counts.json`。

可在 `multiroute_*.py` 启动前设置：

- `AUTO_RESTART_FROM_ROUTE=<route后缀>`（推荐）
  - 例：`AUTO_RESTART_FROM_ROUTE=7`
  - 含义：从 route 7 开始、从第一个 config 重新录制。
  - 会自动把全局计数回退到 `7:1`（即 route 7 第一个 `record_start` 之前），不需要手动改 `_action_counts.json`。
  - 回退时会按完整 route 序列重建到目标 route 前，所以 **pull 后第一次回退也不需要手动改全局计数**。
- `AUTO_ROLLBACK_CHECKPOINT=<route后缀>:<record_start序号>`（高级）
  - 例：`AUTO_ROLLBACK_CHECKPOINT=7:17`
  - 含义：把全局计数精确回退到「route 7 的第 17 个 `record_start` 执行之前」。
- `AUTO_ROLLBACK_ONLY=1`
  - 仅执行回档并写回 `_action_counts.json`，随后退出，不开始录制。

如果不设置这些环境变量，脚本行为与原来一致。
