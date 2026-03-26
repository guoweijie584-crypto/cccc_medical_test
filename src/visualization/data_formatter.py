"""
可视化数据格式化模块

将评测数据格式化为 CCCC Web UI PresentationCard 可用的格式
支持: markdown, table, image (base64)
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class CCCCPresentationFormatter:
    """CCCC 演示数据格式化器"""
    
    def __init__(self, output_dir: str = "data/visualization"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def format_dashboard(self, evaluation_summary: Dict, iteration_history: List[Dict]) -> Dict:
        """格式化主控面板数据"""
        summary = evaluation_summary.get('summary', {})
        overall_score = summary.get('overall_score', 0)
        
        trend = "+0.00"
        if len(iteration_history) >= 2:
            initial = iteration_history[0].get('overall_score', 0)
            final = iteration_history[-1].get('overall_score', 0)
            trend = f"{final - initial:+.2f}"
        
        return {
            "type": "dashboard",
            "title": "血糖管理 Agent 自进化系统",
            "timestamp": datetime.now().isoformat(),
            "score": overall_score,
            "trend": trend,
            "iterations": len(iteration_history),
            "dimensions": {
                "medical_accuracy": summary.get('medical_accuracy', 0),
                "safety": summary.get('safety', 0),
                "completeness": summary.get('completeness', 0),
                "personalization": summary.get('personalization', 0),
                "consistency": summary.get('consistency', 0)
            },
            "category_scores": summary.get('category_scores', {})
        }
    
    def export_for_cccc_ui(self, data: Dict, filename: str):
        """导出为 CCCC Web UI 可用的 JSON 文件"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[导出] {output_path}")
        return output_path
    
    def generate_all_presentations(self):
        """生成所有演示数据"""
        # 加载评测数据
        eval_path = "tests/output/run_20260325_005407_iter0/evaluation_results.json"
        with open(eval_path, 'r', encoding='utf-8') as f:
            evaluation_data = json.load(f)
        
        # 加载迭代历史
        iteration_history = []
        csv_path = "tests/output/iteration_summary.csv"
        if Path(csv_path).exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    iteration_history.append({
                        'overall_score': float(row.get('overall_score', 0)),
                        'medical_accuracy': float(row.get('medical_accuracy', 0)),
                        'safety': float(row.get('safety', 0))
                    })
        
        # 生成仪表板数据
        dashboard = self.format_dashboard(evaluation_data, iteration_history)
        self.export_for_cccc_ui(dashboard, "dashboard.json")
        
        print("\n[完成] 演示数据已生成")
        return dashboard


def main():
    formatter = CCCCPresentationFormatter()
    formatter.generate_all_presentations()


if __name__ == '__main__':
    main()
