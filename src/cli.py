
import argparse
import datetime
from src.agent_core import PubMedAgent
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="PubMed智能文献分析助手")
    
    # 命令行参数
    parser.add_argument("keyword", type=str, help="搜索关键词")
    parser.add_argument("-o", "--output", type=Path, default="./reports", 
                       help="报告输出目录")
    parser.add_argument("-m", "--max", type=int, default=3,
                       help="最大处理文献数")
    parser.add_argument("--email", type=str, 
                       help="覆盖默认邮箱配置")
    
    args = parser.parse_args()
    
    # 初始化智能体
    agent = PubMedAgent()
    if args.email:
        agent.email = args.email
    
    # 执行任务
    report = agent.run(
        keyword=args.keyword,
        max_articles=args.max
    )
    
    # 保存报告
    args.output.mkdir(exist_ok=True)
    filename = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
    (args.output / filename).write_text(report)
    
    print(f"报告已生成：{filename}")

if __name__ == "__main__":
    main()