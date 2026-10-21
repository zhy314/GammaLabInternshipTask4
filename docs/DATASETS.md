# 数据集说明（DATASETS）

本项目使用三份公开 HuggingFace 数据集作为真实样例。所有数据均**不随仓库提交**（见 `.gitignore` 中的 `data/raw/`、`data/clean/`）；仓库仅保留 `data/samples/` 下不足百行的脱敏小样本用于端到端演示。

拉取命令：

```bash
pip install datasets
python scripts/fetch_datasets.py all   # 或 adult / titanic / data_jobs
```

---

## 1. UCI Adult Census Income

- HuggingFace 仓库：`scikit-learn/adult-census-income`
- URL：<https://huggingface.co/datasets/scikit-learn/adult-census-income>
- 原始来源：UCI Machine Learning Repository, Adult Dataset
- 许可：CC BY 4.0（UCI 原始许可）
- 规模：约 48,842 行 × 15 列
- 字段：`age, workclass, fnlwgt, education, education-num, marital-status, occupation, relationship, race, sex, capital-gain, capital-loss, hours-per-week, native-country, income`
- 脏数据特征：
  - 多列缺失值以字符串 `?` 编码
  - 字符串字段存在前导空格
  - 存在少量全行重复
- 适用演示：**缺失标记归一化、`median`/`mode` 填补、枚举校验**。
- 对应配置：[configs/adult.yaml](../configs/adult.yaml)

## 2. Titanic

- HuggingFace 仓库：`mstz/titanic`
- URL：<https://huggingface.co/datasets/mstz/titanic>
- 原始来源：Kaggle Titanic competition（公开版本）
- 许可：公共领域（Kaggle 公开数据）
- 规模：约 1,300 行 × 12 列
- 字段：`PassengerId, Survived, Pclass, Name, Sex, Age, SibSp, Parch, Ticket, Fare, Cabin, Embarked`
- 脏数据特征：
  - `Age`、`Cabin` 大量缺失（`Cabin` 缺失率 >70%）
  - `Embarked` 偶发缺失
  - 文本列大小写与空白不规范
- 适用演示：**高缺失率处理（`constant` 填充）、按主键去重、枚举约束**。
- 对应配置：[configs/titanic.yaml](../configs/titanic.yaml)

## 3. Data Jobs (lukebarousse)

- HuggingFace 仓库：`lukebarousse/data_jobs`
- URL：<https://huggingface.co/datasets/lukebarousse/data_jobs>
- 原始来源：公开抓取的数据分析岗位招聘信息
- 许可：仓库未明确声明；按作者 README 为学习/研究用途
- 规模：约 785,000 行 × 20+ 列
- 字段（部分）：`job_title_short, job_title, job_location, job_schedule_type, job_work_from_home, salary_year_avg, salary_hour_avg, company_name, ...`
- 脏数据特征：
  - 大量重复（同一岗位重复发布）
  - 薪资字段存在 null、0、极端离群值
  - 日期字段格式不统一
  - 字符串大小写/空白混乱
- 适用演示：**大规模数据下的 subset 去重、数值范围过滤、`coerce` 策略下的阈值保护**。
- 对应配置：[configs/data_jobs.yaml](../configs/data_jobs.yaml)

---

## 4. 版本固定（Revision Pinning）

[scripts/fetch_datasets.py](../scripts/fetch_datasets.py) 的 `DATASETS` 字典中保留了 `revision` 字段，当前默认为 `"main"`。要获得完全可复现的实验，请将其替换为具体 commit SHA（可在 HuggingFace 数据集页面"Files and versions"中获取），例如：

```python
"revision": "a1b2c3d4e5...",
```

同时建议在 `run_manifest.json` 之外，把当前使用的 revision 记录到实验笔记中。

---

## 5. 数据划分

本项目**不涉及训练/验证/测试划分**——它是一个清洗工具，不做建模。所有数据按原始发布形式一次性进行清洗；下游任务（如分类）由使用者自行划分。

---

## 6. 本地样例

- [data/samples/adult_sample.csv](../data/samples/adult_sample.csv)：从 Adult 手工摘录 10 行，覆盖 `?` 缺失标记、重复行、`?` 国籍等场景；在不下载完整 HF 数据集的情况下即可演示端到端流水线。
