#!/usr/bin/env python3
"""
股票政策查询工具演示脚本

这个脚本演示了如何使用StockPolicyTool来查询股票市场相关的政策信息。
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tool.stock.stock_policy import StockPolicyTool


async def demo_stock_policy_tool():
    """演示股票政策工具的各种功能"""

    print("🚀 股票政策查询工具演示")
    print("=" * 50)

    # 创建工具实例
    tool = StockPolicyTool()

    # 演示1: 查询监管政策
    print("\n📋 演示1: 查询监管政策")
    print("-" * 30)
    result = await tool.execute(
        query="注册制", policy_type="regulation", market="ab", time_range="recent"
    )
    print(result.output)

    # 演示2: 查询交易规则
    print("\n📋 演示2: 查询交易规则")
    print("-" * 30)
    result = await tool.execute(
        query="交易规则", policy_type="trading", market="all", time_range="month"
    )
    print(result.output)

    # 演示3: 查询上市制度
    print("\n📋 演示3: 查询上市制度")
    print("-" * 30)
    result = await tool.execute(
        query="上市", policy_type="listing", market="ab", time_range="quarter"
    )
    print(result.output)

    # 演示4: 查询公告通知
    print("\n📋 演示4: 查询公告通知")
    print("-" * 30)
    result = await tool.execute(
        query="休市", policy_type="announcement", market="all", time_range="recent"
    )
    print(result.output)

    # 演示5: 查询全部政策
    print("\n📋 演示5: 查询全部政策")
    print("-" * 30)
    result = await tool.execute(
        query="政策", policy_type="all", market="all", time_range="year"
    )
    print(result.output)

    print("\n✅ 演示完成！")


async def interactive_demo():
    """交互式演示"""

    print("🎯 交互式股票政策查询演示")
    print("=" * 50)

    tool = StockPolicyTool()

    while True:
        print("\n请选择查询类型:")
        print("1. 监管政策")
        print("2. 交易规则")
        print("3. 上市制度")
        print("4. 公告通知")
        print("5. 全部政策")
        print("0. 退出")

        choice = input("\n请输入选择 (0-5): ").strip()

        if choice == "0":
            print("👋 再见！")
            break

        if choice not in ["1", "2", "3", "4", "5"]:
            print("❌ 无效选择，请重新输入")
            continue

        # 获取查询关键词
        query = input("请输入查询关键词: ").strip()
        if not query:
            print("❌ 查询关键词不能为空")
            continue

        # 获取市场范围
        print("\n请选择市场范围:")
        print("1. 全部市场")
        print("2. A股")
        print("3. 港股")
        print("4. 美股")
        market_choice = input("请输入选择 (1-4): ").strip()
        market_map = {"1": "all", "2": "ab", "3": "hk", "4": "us"}
        market = market_map.get(market_choice, "all")

        # 获取时间范围
        print("\n请选择时间范围:")
        print("1. 最近")
        print("2. 近一月")
        print("3. 近一季度")
        print("4. 近一年")
        time_choice = input("请输入选择 (1-4): ").strip()
        time_map = {"1": "recent", "2": "month", "3": "quarter", "4": "year"}
        time_range = time_map.get(time_choice, "recent")

        # 映射政策类型
        policy_type_map = {
            "1": "regulation",
            "2": "trading",
            "3": "listing",
            "4": "announcement",
            "5": "all",
        }
        policy_type = policy_type_map[choice]

        try:
            print(f"\n🔍 正在查询: {query}...")
            result = await tool.execute(
                query=query,
                policy_type=policy_type,
                market=market,
                time_range=time_range,
            )
            print("\n📊 查询结果:")
            print("-" * 30)
            print(result.output)

        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")


if __name__ == "__main__":
    print("选择演示模式:")
    print("1. 自动演示")
    print("2. 交互式演示")

    mode = input("请输入选择 (1-2): ").strip()

    if mode == "1":
        asyncio.run(demo_stock_policy_tool())
    elif mode == "2":
        asyncio.run(interactive_demo())
    else:
        print("❌ 无效选择")
