# 实现与验证报告（RUBRIC_REPORT）

本文档对照 Task4 公开 Rubric 的四个维度（正确性与边界验证 / 实现与目标库集成 / 可复现的实验依据 / 讲解与分析）给出具体落点与证据。

---

## 1. 正确性与边界验证（40 分）

### 1.1 核心能力

| 需求 | 实现位置 | 验证测试 |
|---|---|---|
| 编码探测与规范化 | [io_utils.detect_encoding](../src/dataclean/io_utils.py)、[cleaners/encoding.normalize_text](../src/dataclean/cleaners/encoding.py) | [tests/test_encoding.py](../tests/test_encoding.py)、[tests/test_io.py::test_detect_encoding_gbk](../tests/test_io.py) |
| 缺失标记 → NaN | [cleaners/missing.mark_missing](../src/dataclean/cleaners/missing.py) | [tests/test_missing.py::test_mark_missing_replaces_markers](../tests/test_missing.py) |
| 多策略填补 | [cleaners/missing.impute](../src/dataclean/cleaners/missing.py) | `test_impute_median_and_mode / test_impute_drop_row / test_impute_constant` |
| 去重 | [cleaners/duplicates.dedupe](../src/dataclean/cleaners/duplicates.py) | [tests/test_duplicates.py](../tests/test_duplicates.py) |
| 非法值检测（dtype/range/enum/regex） | [cleaners/illegal.apply_illegal](../src/dataclean/cleaners/illegal.py) | [tests/test_illegal.py](../tests/test_illegal.py) |
| 退出码契约 | [exit_codes.py](../src/dataclean/exit_codes.py)、[cli.py](../src/dataclean/cli.py) | [tests/test_cli.py](../tests/test_cli.py) 中 4 个退出码断言 |

### 1.2 边界场景

| 边界 | 表现 | 测试 |
|---|---|---|
| 文件不存在 | 退出码 12 | `test_input_not_found_exit_12` |
| 配置非法（dtype 未知） | 退出码 11 | `test_config_invalid_exit_11` |
| 非法值比例超阈值 | 退出码 20 | `test_illegal_ratio_exceeded_exit_20`、`test_ratio_exceeded_raises` |
| `on_violation=fail` + 任一违规 | 退出码 20 | `test_fail_mode_raises_on_any_violation` |
| 空输入（仅表头） | 退出码 0，不触发 EMPTY_AFTER_CLEAN | `test_e2e_empty_input` |
| GBK 编码 | `detect_encoding` 返回 `gbk/gb18030`，解码正常 | `test_detect_encoding_gbk` |
| 全空列 / 全重复 | 由 `impute` + `dedupe` 行为覆盖 | `test_impute_median_and_mode`、`test_dedupe_full_row` |
| 子集去重列缺失 | 软失败，退化到全行去重 | `test_dedupe_missing_subset_column_falls_back` |
| 子命令 `inspect` | 输出 JSON，可脚本解析 | `test_inspect_prints_json` |
| `validate` dry-run | 不写文件 | `test_validate_dry_run` |

### 1.3 实际运行

```
pytest tests/
...
40 passed in 0.27s
```

对仓库样例 `data/samples/adult_sample.csv` 的真实运行结果（10 行 → 9 行）：

- 3 个 `?` 标记成功替换为 NaN
- `age`/`occupation`/`native-country` 各填补 1 个
- 去除 1 行完全重复
- 0 个非法值，退出码 0
- 产物 `data/clean/adult_sample.clean.csv`，manifest `runs/adult_sample.manifest.json`

---

## 2. 实现与目标库集成（20 分）

### 2.1 接口质量

- 单一入口 `dataclean`（在 `pyproject.toml` 中声明 `console_scripts`），三条清晰的子命令：`clean / inspect / validate`。
- 参数命名使用 Linux 风格 `--kebab-case`，与 pandas CLI、scikit-learn CLI 等生态一致。
- 退出码契约文档化（README §5），下游 shell / CI 可据此分支。

### 2.2 代码质量

- 严格的类型注解（`from __future__ import annotations` + 现代泛型）
- 异常层次：`DataCleanError` 作为基类，所有具体错误携带 `exit_code`；CLI 层统一 `_handle` 翻译为退出码。
- 包内绝对导入 + `src/` 布局，避免工作目录相关的导入陷阱。
- 零硬编码路径；所有示例使用相对路径。

### 2.3 与目标生态集成

- 规则文件采用 YAML（人类可读、Git diff 友好），语义接近 Great Expectations / pandera 的"schema + 违规策略"模式。
- Manifest schema 版本化（`"schema": "dataclean.manifest.v1"`），利于未来变更。
- 可通过 `pip install -e .` 开发安装，与 Jupyter / 自动化脚本自由组合。

---

## 3. 可复现的实验依据（25 分）

### 3.1 环境

- Python：3.9 / 3.10（`environment.yml` 固定 3.10，`pyproject.toml` 要求 >=3.9）
- 关键依赖版本（本次运行 manifest 记录）：
  - pandas 2.3.3
  - click 8.1.8
  - PyYAML 6.0.3
  - chardet 5.2.0
- OS：Windows 10（`Windows-10-10.0.22631-SP0`）；Linux / macOS 兼容。
- 硬件：对本流水线无特殊要求（纯 CPU + 内存，内存需能容纳整表 DataFrame）。

### 3.2 复现命令

```bash
# 一次性
conda env create -f environment.yml && conda activate dataclean
pip install -e .

# 复现样例
dataclean -v clean \
  --input  data/samples/adult_sample.csv \
  --output data/clean/adult_sample.clean.csv \
  --config configs/adult.yaml \
  --report runs/adult_sample.manifest.json

# 复现完整数据集（需联网 HuggingFace）
python scripts/fetch_datasets.py adult
bash examples/run_adult.sh
```

### 3.3 数据来源与划分

见 [DATASETS.md](DATASETS.md)。本工具只做清洗，不做训练/验证/测试划分。

### 3.4 日志与结果

- 结构化 stderr 日志（`-v` 开启 INFO、`-vv` 开启 DEBUG）
- `run_manifest.json` 完整记录：输入/输出/配置的 SHA-256、库版本、每阶段统计、退出码
- 相同输入 + 相同配置 + 相同版本 ⇒ 相同输出 SHA-256（可脚本比对）

实测样例 manifest（节选）：

```
input.sha256  : eb49028a085953b26e536dbec2a8c155c063e871f38fa56b023ca2f132b3c919
output.sha256 : 8cb9aa62bdb2c82c03a15c33473faff007720e5dbc5473c0dcd94d06b138dd0a
config.sha256 : 68df0e4366e46a0269fb1d0c8a8b8becd88eb74083504d7e2bfc01d76ae215b0
exit_code     : 0
```

---

## 4. 讲解与分析（15 分）

### 4.1 从"公式"到代码

本任务没有传统意义的数学公式，但各阶段均有可审计的"判定式"，列于 [DESIGN.md §2 规则→代码对照](DESIGN.md#2-规则--代码对照)。以非法值检测为例：

```
违规判定 = (dtype_coercion_fail)
        OR ((numeric < lo) OR (numeric > hi))
        OR (not in enum)
        OR (not regex.fullmatch)

violation_ratio = total_violations / (rows * checked_columns)
if violation_ratio > max_ratio: exit(20)
```

### 4.2 设计选择

详见 [DESIGN.md §3](DESIGN.md#3-关键设计选择与权衡)，关键三条：

1. **全部按字符串读入 CSV**：保留原始形态，让缺失/非法判定可审计。
2. **阶段顺序 encoding → missing → dedupe → illegal**：先规范再比对，减少"看似不同实则相同"的误判。
3. **max_ratio 阈值保护**：避免 `coerce` 把大量数据静默变 NaN。

### 4.3 结果差异

Adult 样例在"仅覆盖缺失标记 + 去重"下行数 10 → 9；若把 `age` 填补策略换为 `drop_row`，则会额外丢弃原本可填补的 1 行。这显示了**策略选择对数据保留率的直接影响**，也是导师可能追问的典型场景。

### 4.4 局限

见 [DESIGN.md §4](DESIGN.md#4-已知局限)。核心短板：全表加载、跨列条件填补未内置、无专门日期规范化模块。
