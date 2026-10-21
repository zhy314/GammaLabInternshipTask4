# dataclean — 可重复的数据清洗流水线

一个基于 Python / pandas / click 的命令行工具，针对表格数据（CSV / JSON / JSONL）执行可配置、可复现的清洗流程：**编码规范化 → 缺失值识别与填补 → 去重 → 非法值检测 → 结构化输出**。每次运行会生成一份 `run_manifest.json`（含输入/输出/配置的 SHA-256、库版本、各阶段统计），用于复现与审计。

> 面向工程实践课程 Task4：以公开 Rubric 为准，演示"规则 → 实现 → 测试 → 文档 → 复现"的完整链路。

---

## 1. 功能概览

| 阶段 | 能力 | 配置项 |
|---|---|---|
| 编码规范化 | 字符串 NFKC 归一化、`strip` 空白、折叠空格 | `encoding_normalize` |
| 缺失值识别 | 自定义缺失标记（如 `?`、`NA`、`null`）→ NaN | `missing.markers` |
| 缺失值填补 | 按列策略：`drop_row` / `mean` / `median` / `mode` / `constant` / `keep` | `missing.strategy` |
| 去重 | 全列或指定键去重，保留 `first` / `last` / 全删 | `duplicates.subset`、`duplicates.keep` |
| 非法值检测 | 数据类型、数值范围、枚举、正则；策略：`fail` / `drop` / `coerce` | `illegal.on_violation` |
| 阈值保护 | 非法值比例超限直接以非零退出码失败 | `illegal.max_ratio` |

---

## 2. 环境与安装

### 2.1 使用 conda（推荐）

```bash
git clone <this-repository-url>
cd <repo>

conda env create -f environment.yml
conda activate dataclean

pip install -e .
```

### 2.2 使用现有 Python / pip

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

验证安装：

```bash
dataclean --version
dataclean --help
```

> 本项目在 Python 3.9 / 3.10 下验证通过，依赖 `pandas>=1.5, click>=8.1, pyyaml>=6.0, chardet>=5.0`。

---

## 3. 快速开始

### 3.1 直接处理仓库自带样例

```bash
dataclean -v clean \
  --input  data/samples/adult_sample.csv \
  --output data/clean/adult_sample.clean.csv \
  --config configs/adult.yaml \
  --report runs/adult_sample.manifest.json
```

### 3.2 从 HuggingFace 拉取完整数据集

```bash
pip install datasets                   # 一次性
python scripts/fetch_datasets.py adult # 或 titanic / data_jobs / all
bash   examples/run_adult.sh
```

### 3.3 其它子命令

```bash
# 探查：打印检测到的编码、dtype、缺失计数
dataclean inspect --input data/samples/adult_sample.csv

# 校验：只走流程不写出，用退出码表示是否通过
dataclean validate \
  --input  data/samples/adult_sample.csv \
  --config configs/adult.yaml
```

---

## 4. CLI 参考

```
dataclean [-v | -vv] COMMAND [OPTIONS]

Commands:
  clean      执行完整清洗并写出结果
  inspect    打印输入文件的基本统计（编码/dtype/缺失）
  validate   dry-run：只跑流水线，不写输出

clean 的常用参数:
  --input PATH                输入文件（CSV / JSON / JSONL）
  --output PATH               输出文件
  --config PATH               YAML 规则文件
  --format [auto|csv|json|jsonl]
  --encoding TEXT             'auto' 使用 chardet 自动探测
  --on-illegal [fail|drop|coerce]       覆盖配置
  --max-illegal-ratio FLOAT             覆盖配置（0..1）
  --report PATH               写出 run_manifest.json
```

---

## 5. 退出码（stable contract）

| 代码 | 含义 |
|---:|---|
| 0  | 成功 |
| 1  | 其它未捕获错误 |
| 2  | CLI 参数非法（click 默认） |
| 10 | 编码无法识别或解码失败 |
| 11 | 配置文件缺失 / 非法 |
| 12 | 输入文件不存在 |
| 13 | 文件格式不受支持 |
| 20 | 非法值比例超过 `max_ratio`，或 `on_violation=fail` 命中 |
| 30 | 清洗后行数为 0 |

CI/CD 可据此分支不同处理（例如 20 发告警、11 直接阻断）。

---

## 6. 配置文件（YAML）

最小示例：

```yaml
encoding_normalize: true

schema:
  columns:
    age: { dtype: int, range: [0, 120] }
    sex: { dtype: string, enum: ["Male", "Female"] }

missing:
  markers: ["?", ""]
  strategy:
    age: median
    default: drop_row

duplicates:
  subset: null
  keep: first

illegal:
  on_violation: coerce   # fail | drop | coerce
  max_ratio: 0.05
```

完整示例见 [configs/adult.yaml](configs/adult.yaml)、[configs/titanic.yaml](configs/titanic.yaml)、[configs/data_jobs.yaml](configs/data_jobs.yaml)。

---

## 7. 测试

```bash
pytest                              # 全部单元 + CLI + E2E 测试
pytest --cov=src/dataclean          # 带覆盖率
```

当前 40 个用例覆盖：

- 四个 cleaner 的正常路径与边界（空输入、单行、全缺失、GBK/UTF-8 混合、枚举/正则违规、越界、全重复等）
- CLI 退出码（0 / 11 / 12 / 20）
- 端到端：CSV 与 JSONL 全流程 + 配置校验

---

## 8. 复现实验

每次 `clean` 运行会产出 `run_manifest.json`：

```json
{
  "schema": "dataclean.manifest.v1",
  "timestamp_utc": "...",
  "input":  { "path": "...", "sha256": "...", "rows": N },
  "output": { "path": "...", "sha256": "...", "rows": M },
  "config": { "path": "...", "sha256": "..." },
  "environment": { "platform": "...", "libraries": { ... } },
  "stages":  { "encoding": {...}, "missing_markers": {...}, "impute": {...},
               "duplicates": {...}, "illegal": {...} },
  "exit_code": 0
}
```

只要输入文件、配置文件、依赖版本一致，结果 SHA-256 应当完全一致。

---

## 9. 项目结构

```
.
├── README.md
├── docs/                 # DESIGN / RUBRIC_REPORT / DATASETS
├── configs/              # 三份数据集的清洗规则
├── src/dataclean/        # 核心代码（CLI / Pipeline / Cleaners / IO）
├── tests/                # pytest 测试 + fixtures
├── scripts/              # HuggingFace 数据拉取脚本
├── examples/             # 端到端运行脚本
├── data/samples/         # 可提交的脱敏小样本（<100 行）
├── environment.yml
├── requirements.txt
└── pyproject.toml
```

---

## 10. 相关文档

- 架构与设计选型：[docs/DESIGN.md](docs/DESIGN.md)
- 对照 Rubric 的实现与验证报告：[docs/RUBRIC_REPORT.md](docs/RUBRIC_REPORT.md)
- 数据集说明（来源 / 许可 / 版本）：[docs/DATASETS.md](docs/DATASETS.md)

---

## 11. 许可

本仓库代码以 MIT License 开源。所引用的公开数据集各自遵循其原始许可，详见 [docs/DATASETS.md](docs/DATASETS.md)。
