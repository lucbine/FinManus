# 股票政策查询工具 (StockPolicyTool)

## 概述

股票政策查询工具是一个专门用于查询股票市场相关政策、法规和公告的工具。它可以帮助投资者、分析师和研究人员快速获取最新的市场政策信息，包括监管政策、交易规则、上市制度和公告通知等。

## 功能特性

### 🎯 核心功能
- **监管政策查询**: 查询证监会、交易所等监管机构发布的最新政策
- **交易规则查询**: 获取交易规则变更、涨跌幅调整等信息
- **上市制度查询**: 了解注册制改革、上市条件等制度变化
- **公告通知查询**: 获取休市安排、指数调整等重要公告

### 🌍 市场覆盖
- **A股市场**: 上海证券交易所、深圳证券交易所
- **港股市场**: 香港联合交易所
- **美股市场**: 纳斯达克、纽约证券交易所
- **全部市场**: 跨市场综合查询

### ⏰ 时间范围
- **最近**: 最新发布的政策信息
- **近一月**: 最近一个月内的政策
- **近一季度**: 最近一个季度的政策
- **近一年**: 最近一年内的政策

## 使用方法

### 基本用法

```python
from app.tool.stock.stock_policy import StockPolicyTool

# 创建工具实例
tool = StockPolicyTool()

# 查询监管政策
result = await tool.execute(
    query="注册制",
    policy_type="regulation",
    market="ab",
    time_range="recent"
)
print(result.output)
```

### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 查询关键词，如"注册制"、"退市制度"等 |
| `policy_type` | string | ❌ | "all" | 政策类型：all/regulation/trading/listing/announcement |
| `market` | string | ❌ | "all" | 市场范围：all/ab/hk/us |
| `time_range` | string | ❌ | "recent" | 时间范围：recent/month/quarter/year |

### 政策类型说明

- **regulation** (监管政策): 证监会、交易所等监管机构发布的政策文件
- **trading** (交易规则): 交易机制、涨跌幅、交易时间等规则变更
- **listing** (上市制度): 上市条件、审核标准、注册制改革等
- **announcement** (公告通知): 休市安排、指数调整、重要通知等
- **all** (全部): 综合查询所有类型的政策信息

### 市场类型说明

- **ab** (A股): 上海证券交易所、深圳证券交易所
- **hk** (港股): 香港联合交易所
- **us** (美股): 纳斯达克、纽约证券交易所
- **all** (全部市场): 跨市场综合查询

### 时间范围说明

- **recent** (最近): 最新发布的政策信息
- **month** (近一月): 最近一个月内的政策
- **quarter** (近一季度): 最近一个季度的政策
- **year** (近一年): 最近一年内的政策

## 使用示例

### 示例1: 查询注册制相关政策

```python
result = await tool.execute(
    query="注册制",
    policy_type="regulation",
    market="ab",
    time_range="recent"
)
```

**输出示例:**
```
查询关键词: 注册制
市场范围: A股
时间范围: 最近
查询时间: 2025-06-26 20:28:13

监管政策信息:

1. 注册制改革配套政策实施细则
   来源: 证监会
   日期: 2024-01-10
   状态: 征求意见中
   摘要: 为配合注册制改革，制定相关配套政策实施细则...
   影响: 简化上市流程，提高市场效率，利好优质企业上市
```

### 示例2: 查询交易规则变更

```python
result = await tool.execute(
    query="交易规则",
    policy_type="trading",
    market="all",
    time_range="month"
)
```

### 示例3: 查询上市制度变化

```python
result = await tool.execute(
    query="上市",
    policy_type="listing",
    market="ab",
    time_range="quarter"
)
```

### 示例4: 查询公告通知

```python
result = await tool.execute(
    query="休市",
    policy_type="announcement",
    market="all",
    time_range="recent"
)
```

### 示例5: 综合查询所有政策

```python
result = await tool.execute(
    query="政策",
    policy_type="all",
    market="all",
    time_range="year"
)
```

## 输出格式

工具返回的结果包含以下信息：

1. **查询信息**: 查询关键词、市场范围、时间范围、查询时间
2. **政策列表**: 按类型分类的政策信息
3. **政策详情**: 每个政策包含标题、来源、日期、状态、摘要、影响等

### 输出结构

```
查询关键词: [关键词]
市场范围: [市场名称]
时间范围: [时间范围]
查询时间: [查询时间]

[政策类型]信息:

1. [政策标题]
   来源: [发布机构]
   日期: [发布日期]
   状态: [政策状态]
   摘要: [政策摘要]
   影响: [市场影响分析]
```

## 集成到系统

### 在Agent中使用

```python
from app.agent.manus import StockManus

# 创建股票分析智能体
agent = StockManus()

# 工具会自动注册到智能体中
# 可以通过自然语言调用股票政策查询功能
```

### 在API中使用

```python
from app.tool.stock.stock_policy import StockPolicyTool

# 在API路由中使用
@router.post("/stock/policy")
async def query_stock_policy(request: PolicyQueryRequest):
    tool = StockPolicyTool()
    result = await tool.execute(**request.dict())
    return result
```

## 测试

运行测试用例：

```bash
# 运行所有测试
python -m pytest tests/test_stock_policy.py -v

# 运行特定测试
python -m pytest tests/test_stock_policy.py::TestStockPolicyTool::test_execute_regulation_policies -v
```

## 演示

运行演示脚本：

```bash
# 自动演示
python examples/stock_policy_demo.py

# 交互式演示
python examples/stock_policy_demo.py
```

## 扩展功能

### 未来计划

1. **实时数据源**: 集成真实的政策数据API
2. **智能分析**: 添加政策影响分析功能
3. **历史对比**: 支持政策历史版本对比
4. **推送通知**: 重要政策变更推送功能
5. **多语言支持**: 支持英文等其他语言

### 自定义扩展

可以通过继承 `StockPolicyTool` 类来扩展功能：

```python
class CustomStockPolicyTool(StockPolicyTool):
    async def _get_custom_policies(self, query: str, market: str, time_range: str) -> str:
        # 实现自定义政策查询逻辑
        pass
```

## 注意事项

1. **数据时效性**: 当前版本使用模拟数据，实际使用时需要集成真实数据源
2. **查询限制**: 建议合理使用查询频率，避免对数据源造成压力
3. **错误处理**: 工具包含完善的错误处理机制，会返回详细的错误信息
4. **并发安全**: 工具支持并发调用，但建议控制并发数量

## 技术支持

如有问题或建议，请通过以下方式联系：

- 提交 Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 邮件联系: support@example.com
- 文档更新: 欢迎提交 Pull Request

---

**版本**: 1.0.0
**更新时间**: 2025-06-26
**维护者**: FinManus Team
