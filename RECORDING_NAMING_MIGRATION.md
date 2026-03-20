# Recording Naming Migration

## 目的

这份文件专门说明录制目录命名规则从旧到新的变化，方便修改主观实验 GUI 的路径解析逻辑。

当前主链使用的 nation 是 `natlan_v2`，录制根目录示例：

```text
/Users/xingzhengpeng/CODEZONE/PCO/Power-Optimization/Recordings/huaweipura
```

## 三代命名规则

### 1. 最老格式

目录结构：

```text
<video_base>/<label>/<country>_<global_action_index>_h<route_suffix>/<config_id>.mp4
```

示例：

```text
run/natlan_21_h30/High_60_High_Low.mp4
move/natlan_1_h2/High_60_High_Low.mp4
glide/natlan_18_h22/High_60_High_Low.mp4
```

字段含义：

- `<label>`：顶层目录名，也是视频标签。
- `<country>`：国家名，如 `natlan`。
- `<global_action_index>`：旧版“同一标签的全局累计计数”。
- `h<route_suffix>`：旧版 route 后缀，`h30` 表示 route `30`。
- `<config_id>`：render config 标识。

旧 GUI 如果是按这个格式写的，通常会依赖：

- 顶层目录推断动作标签
- 子目录名里的 `global_action_index`
- 子目录名里的 `route_suffix`

问题：

- `global_action_index` 依赖历史录制顺序，不稳定。
- 同一路线重录会影响后面所有同标签视频的编号。

### 2. 中间过渡格式

目录结构：

```text
<video_base>/<label>/<country>_r<route:02d>_s<segment:02d>/<config_id>.mp4
```

示例：

```text
run/natlan_r30_s03/High_60_High_Low.mp4
move/natlan_r02_s02/High_60_High_Low.mp4
glide/natlan_r22_s01/High_60_High_Low.mp4
```

字段含义：

- `r<route:02d>`：route 编号，固定两位。
- `s<segment:02d>`：该 route 内按 `record_start` 总顺序编号。

这个格式已经是过渡态，现在不再作为最终规则。

### 3. 当前最终格式

目录结构：

```text
<video_base>/<label>/<country>_r<route:02d>_<label><occurrence:02d>/<config_id>.mp4
```

示例：

```text
run/natlan_r30_run02/High_60_High_Low.mp4
move/natlan_r02_move01/High_60_High_Low.mp4
glide/natlan_r22_glide01/High_60_High_Low.mp4
```

字段含义：

- `<label>`：顶层目录名，也是标签。
- `r<route:02d>`：route 编号，固定两位。
- `<label><occurrence:02d>`：同一条 route 内，该 label 的第几次出现。

关键点：

- 编号不再是整条 route 的 `s01/s02/s03`。
- 编号改成“同一 label 在该 route 内的出现次数”。

例如一条 route 的录制顺序如果是：

```text
glide -> run -> run
```

则目录会是：

```text
glide01
run01
run02
```

而不是：

```text
s01
s02
s03
```

## 从旧到新的转换规则

### 旧格式 -> 当前格式

通用规则：

1. 顶层 `<label>` 目录保持不变。
2. 子目录中的 `global_action_index` 被彻底移除。
3. `h<route_suffix>` 改成 `r<route_suffix:02d>`。
4. 新增 `<label><occurrence:02d>`，其中 `occurrence` 不是全局计数，而是该 label 在该 route 内的出现次序。

示例：

```text
run/natlan_21_h30/... -> run/natlan_r30_run01/...
run/natlan_22_h30/... -> run/natlan_r30_run02/...
move/natlan_1_h2/...  -> move/natlan_r02_move01/...
glide/natlan_18_h22/... -> glide/natlan_r22_glide01/...
```

### 中间格式 -> 当前格式

通用规则：

1. 顶层 `<label>` 目录保持不变。
2. `s<segment:02d>` 被替换成 `<label><occurrence:02d>`。
3. `occurrence` 的计算基于当前 route 文件中相同 label 的出现顺序。

示例：

```text
run/natlan_r30_s01/... -> run/natlan_r30_run01/...
climb/natlan_r30_s02/... -> climb/natlan_r30_climb01/...
run/natlan_r30_s03/... -> run/natlan_r30_run02/...
```

## GUI 解析建议

### 旧格式正则

```regex
^(?P<country>[a-z]+)_(?P<global_action_index>\d+)_h(?P<route_suffix>\d+)$
```

### 中间格式正则

```regex
^(?P<country>[a-z]+)_r(?P<route_suffix>\d{2})_s(?P<segment_index>\d{2})$
```

### 当前格式正则

```regex
^(?P<country>[a-z]+)_r(?P<route_suffix>\d{2})_(?P<label>[a-z_]+)(?P<occurrence>\d{2})$
```

GUI 当前应当从路径里解析这些字段：

- 顶层目录名 `label_folder`
- `country`
- `route_suffix`
- `label`
- `occurrence`
- `config_id`

建议做一个一致性检查：

- `label_folder` 应当和目录名里解析出的 `label` 一致

例如：

```text
.../run/natlan_r30_run02/High_60_High_Low.mp4
```

应解析成：

- `label_folder = run`
- `country = natlan`
- `route_suffix = 30`
- `label = run`
- `occurrence = 2`
- `config_id = High_60_High_Low`

## 一个很重要的变化

当前最终格式里，目录名**不能单独恢复 route 内所有片段的整体先后顺序**。

原因：

- `occurrence` 只在同一 label 内递增
- 不再保留统一的 `s01/s02/s03`

例如：

```text
glide01
run01
run02
```

你可以知道：

- `run02` 是这个 route 里第二个 `run`

但你**不能只靠目录名**判断它是不是整条 route 的第 2 段或第 3 段。

如果 GUI 需要恢复 route 内整体播放顺序，必须读取：

```text
routes/natlan_v2/<route_suffix>.py
```

然后按 route 里的 `record_start` 顺序展开。

## 当前实盘数据状态

`huaweipura` 目录已经迁到当前最终格式：

- 不再有最老的 `natlan_1_h2` 这种目录
- 也不再有中间态的 `natlan_r02_s03` 这种目录

当前像下面这样：

```text
run/natlan_r30_run02
glide/natlan_r22_glide01
swim/natlan_r20_swim02
```

## 例外情况

`route 22` 当前只保留了一个有效目录：

```text
glide/natlan_r22_glide01
```

缺失：

- `move01`
- `climb01`

所以 GUI 侧不要假设“某个 route 只要出现了，就一定拥有完整的所有 occurrence 目录”。
