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

## 兼容性说明（与原 routes）

- 路线文件（`routes/*`）不需要改。
- `engine/runner.py` 的调用方式不变，仍通过 `GLOBAL_ACTIONS_MODULE` 动态加载动作模块。
- 只要脚本正确指向 `actions.actions_<device>`，原有 route 的动作名可以按原流程执行。

注意：兼容性指“执行链路不破坏”。动作落点精度取决于分辨率是否正确、以及后续是否需要补少量 `OFFSETS`。
