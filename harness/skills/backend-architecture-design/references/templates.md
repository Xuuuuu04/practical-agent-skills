# 模板

以下代码模板都是示意，类名和函数名要等框架实现确定后再统一；业务内容是虚构的例子，只用来展示写法。

## 项目目录

```
project_root/
  AGENTS.md                     # 给 AI 看的项目入口说明
  server/
    framework/                  # 框架层：入口、注册、按顺序执行、数据抽象、运行轨迹、质量检查
    modules/                    # 业务模块，每个模块一个文件夹
    api_versions/               # 各接口版本的请求和响应格式约定，以及转换成业务核心数据格式的代码
    tests/
    deploy/                     # 部署脚本、环境检查、负载检查、Dockerfile
    .env.example
  docs/
    business/                   # 业务文档，每个业务单元一份
```

## 模块目录

```
server/modules/
  order_refund_calculation/     # 包名用简单英文，完整说明用途
    README.md                   # 模块说明，有行数上限
    module_manifest.py          # 模块清单：对外接口、依赖及原因
    process_graph.py            # 执行顺序图
    data_contracts.py           # 本模块使用的数据格式约定
    public_interface.py         # 其他模块只能通过这里调用本模块
    components/                 # 组件，每个文件只做一件事
      load_refund_records.py
      calculate_refund_amount.py
      save_refund_result.py
    tests/
      test_refund_process.py
```

## 模块清单

```python
MODULE = ModuleManifest(
    name="order_refund_calculation",
    purpose="根据退款记录计算每笔订单的实际退款金额，结果供财务对账页面使用",
    provides=[RefundCalculationInterface],
    depends_on=[
        Dependency(
            module="order_records",
            interface="OrderQueryInterface",
            reason="读取订单的实付金额，作为退款金额的上限",
        ),
    ],
)
```

## 执行顺序图

```python
REFUND_PROCESS = ProcessGraph(
    name="calculate_order_refund",
    steps=[
        Step(load_refund_records),
        Step(calculate_refund_amount),
        Step(save_refund_result, when="refund_amount_changed"),
    ],
)
```

## 数据格式约定

```python
class RefundResult(DataContract):
    order_id: str = Field(description="订单编号，来自订单平台")
    paid_amount: Decimal = Field(description="实付金额：商品原价减去优惠券后的金额，单位元")
    refund_amount: Decimal = Field(description="本次退款金额，不超过实付金额，单位元")
```

## 模块 README

````markdown
# 订单退款计算

## 业务用途
根据退款记录计算每笔订单的实际退款金额，结果供财务对账页面使用。

## 对外接口
（由模块清单生成，不手写）

## 依赖
（由模块清单生成，不手写）

## 处理流程
读取退款记录，计算退款金额，金额有变化时保存结果。执行顺序图见 `process_graph.py`。

## 为什么这样设计
退款金额以实付金额为上限，因为优惠券部分不退现金。计算和保存拆成两个组件，是为了在运行轨迹里分别看到计算结果和保存结果。
````

## 业务文档

````markdown
# 财务对账

## 这个功能给谁用、解决什么问题
财务人员每天对比检查前一天的订单收入和退款，找出金额对不上的订单。

## 业务流程
```mermaid
flowchart LR
  A[读取前一天的订单] --> B[读取退款记录]
  B --> C[计算每笔订单的退款金额]
  C --> D[生成对账表]
```

## 计算规则
退款金额取申请退款金额和实付金额中较小的一个。优惠券部分不退现金。

## 字段说明
| 字段 | 含义 | 来源 |
| --- | --- | --- |
| 实付金额 | 商品原价减去优惠券后的金额，单位元 | 订单平台 |
| 退款金额 | 本次实际退还给顾客的金额，单位元 | 本系统计算 |

## 权限规则
财务人员可以查看本公司的对账数据；其他公司的订单与收款信息不可见。

## 保存规则
同一订单的退款结果与对账结果一起保存，任一失败时不保留本次修改。
````

## 根目录 AGENTS.md

项目根目录 AGENTS.md 的格式和维护方法，以 project-agents-md Skill 为准，这里不再单独给模板。基于本框架的项目，在它的"不要做的事"一节里至少写上：

- 导入其他模块的内部文件。原因：依赖关系会藏进代码，注册表就看不出谁调用了谁。
- 组件之间直接调用。原因：调用顺序应该集中写在执行顺序图里，否则只能读完代码才知道流程。
- 在业务模块里写宽泛的异常捕获。原因：异常由执行顺序图的执行器统一处理，模块里捕获会把真正的错误藏起来。
- 在业务模块里按接口版本写分支。原因：版本只存在于接口层，业务核心只有一份。
