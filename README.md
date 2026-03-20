# Auto_Scripts_v4

## 当前保留链路

项目已经收敛到 `routes/natlan_v2` 一条主链，只保留三类入口：

- `debug_multi_route_*.py`：测试多路径切换，不录制。
- `multiroute_*.py`：批量应用 render config 并录制多路径。
- `test_*.py` / `test_*_v2.py`：单路径调试、route 设计和 portal 验证入口。

## 核心模块

- `actions/global_actions.py`：统一动作实现、分辨率映射和 offset 叠加。
- `actions/actions_*.py`：每台设备选择自己的 mapping 和 offsets。
- `mapping/*.py`：设备分辨率定义。
- `config/switcher.py`：应用 render config，并按当前动作模块分辨率自动映射 tap/swipe 坐标。
- `recording/recorder.py` / `recording/scrcpy_recorder.py`：录屏封装。
- `engine/runner.py`：导出当前动作表和传送动作。
- `engine/route_segments.py`：根据 route 定义生成稳定 segment 身份和输出路径。

## Portal 与 Render Config 规则

- `huaweipura` 是基线设备和基线坐标源。
- route 文件里的 `PORTAL` / `NEXT_PORTAL` 都按 `huaweipura` ADB 横屏坐标维护。
- 其他设备只做按分辨率比例缩放，不做额外旋转或 portrait-to-landscape 转换。
- `render_configs` 是默认基线 render config 来源。
- 设备脚本在运行时按当前动作模块分辨率自动缩放 json 里的 `tap/swipe` 坐标。

## Multi-route 录制规则

- `route` 是最小重录单位。
- 每次重录某条 route 时，会先清理该 route 的稳定输出目录，再完整重跑该 route 的全部 config。
- 不再使用 `_action_counts.json`、`SKIP_RECORDED`、rollback checkpoint 或全局计数回档。
- 多路径录制输出按稳定路径写入：

```text
<video_base>/<label>/<country>_r<route:02d>_<label><occurrence:02d>/<config_id>.mp4
```

示例：

- `glide/natlan_r07_glide02/High_60_High_Low.mp4`
- `move/natlan_r22_move02/High_60_High_Low.mp4`
- `run/natlan_r30_run03/High_60_High_Low.mp4`

occurrence 编号规则：

- 编号按同一 label 在单条 route 内出现的次数递增。
- 例如一条 route 里依次录到 `glide`、`run`、`run`，目录会是 `glide01`、`run01`、`run02`。
- 不再使用整条 route 的统一 `s01/s02/s03` 顺序命名。

标签规则：

- 标签由每个 `record_start` 之后第一个真实动作决定。
- 当前不会重命名 `move`。
- `walk` 是新注册的显式动作；如果 route 里写的是 `walk`，标签就是 `walk`。

## Multi-route 控制项

活跃控制面只保留 route 级别：

- `ROUTE_SUFFIXES`
- `SKIP_ROUTE_SUFFIXES`
- `START_FROM_ROUTE`
- `END_AT_ROUTE`

对应环境变量：

- `AUTO_SKIP_ROUTE_SUFFIXES`
- `AUTO_START_FROM_ROUTE`
- `AUTO_END_AT_ROUTE`

每条 route 默认最多采集 `TOTAL_CONFIGS_PER_ROUTE` 个 config，默认从 `render_configs` 目录按排序取前 N 个。

## 设备接入

1. 复制 `mapping/device_template.py` 为 `mapping/<device>.py`，填入真实 `WIDTH/HEIGHT`。
2. 复制 `actions/actions_device_template.py` 为 `actions/actions_<device>.py`，设置 `MAPPING_MODULE` 和 `OFFSETS`。
3. 在对应测试或录制脚本里把 `GLOBAL_ACTIONS_MODULE` 指向 `actions.actions_<device>`。
4. 先用空 `OFFSETS = {}` 验证映射，再只对偏差动作补少量 offset。

## Offset 规则

最终坐标 = 映射后的坐标 + `GLOBAL` + `GROUP` + `POINT`

- `GLOBAL`：全局偏移
- `GROUP`：动作组偏移，例如 `MOVE`、`TURN`、`ATTACK`
- `POINT`：单个点位偏移，例如 `MOVE_START`、`TURN_180_R`
