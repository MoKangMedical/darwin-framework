"""
达尔文进化框架 — 通用进化引擎

核心逻辑：
1. 读取项目中的"可进化资产"（SKILL.md, prompts, configs）
2. 8维度评分系统评估当前状态
3. Agent-A 提出改进（单一改动）
4. Agent-B 独立评分
5. 棘轮：分数升了commit，降了revert
6. Human checkpoint：每轮暂停等人确认
"""

import os
import json
import subprocess
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


# ============================================
# 8维度评分系统
# ============================================

SCORING_DIMENSIONS = {
    # === 结构维度 (60分) ===
    "frontmatter": {
        "name": "Frontmatter规范性",
        "max_score": 8,
        "category": "structure",
        "checks": [
            "name字段存在且有意义",
            "description描述清晰（>20字）",
            "triggers触发词覆盖主要场景",
            "category分类正确",
        ]
    },
    "workflow_clarity": {
        "name": "工作流清晰度",
        "max_score": 15,
        "category": "structure",
        "checks": [
            "步骤编号连续无跳跃",
            "每步有明确的输入输出",
            "步骤间逻辑关系清晰",
            "有明确的起点和终点",
        ]
    },
    "error_handling": {
        "name": "异常处理",
        "max_score": 10,
        "category": "structure",
        "checks": [
            "有边界条件处理（空输入/模糊输入）",
            "有错误恢复路径",
            "有超时/失败的兜底方案",
        ]
    },
    "checkpoints": {
        "name": "确认检查点",
        "max_score": 7,
        "category": "structure",
        "checks": [
            "关键决策前有用户确认",
            "不确定时主动澄清",
            "有可选的自动/手动模式",
        ]
    },
    "specificity": {
        "name": "指令具体性",
        "max_score": 15,
        "category": "structure",
        "checks": [
            "指令可直接执行无需脑补",
            "有具体的示例/模板",
            "参数有明确的取值范围",
            "输出格式有明确要求",
        ]
    },
    "path_integrity": {
        "name": "路径完整性",
        "max_score": 5,
        "category": "structure",
        "checks": [
            "引用的文件路径真实存在",
            "无悬空引用",
        ]
    },
    # === 效果维度 (40分) ===
    "architecture": {
        "name": "架构合理性",
        "max_score": 15,
        "category": "effectiveness",
        "checks": [
            "整体结构逻辑自洽",
            "职责边界清晰",
            "无冗余/重复步骤",
        ]
    },
    "real_world_output": {
        "name": "实测输出质量",
        "max_score": 25,
        "category": "effectiveness",
        "checks": [
            "用真实prompt测试",
            "输出符合预期",
            "无幻觉/错误信息",
            "用户体验流畅",
        ]
    },
}


@dataclass
class ScoreResult:
    """单次评分结果"""
    total: int = 0
    max_total: int = 100
    dimensions: dict = field(default_factory=dict)
    timestamp: str = ""
    scorer: str = ""  # "agent-b" or "human"
    notes: str = ""


@dataclass 
class EvolutionRound:
    """一轮进化记录"""
    round_num: int = 0
    before_score: int = 0
    after_score: int = 0
    improved: bool = False
    target_dimension: str = ""
    change_description: str = ""
    change_diff: str = ""
    commit_hash: str = ""
    reverted: bool = False
    timestamp: str = ""


@dataclass
class EvolutionReport:
    """进化报告"""
    project_path: str = ""
    asset_path: str = ""
    baseline_score: int = 0
    final_score: int = 0
    rounds: list = field(default_factory=list)
    total_rounds: int = 0
    successful_rounds: int = 0
    reverted_rounds: int = 0
    created_at: str = ""


class DarwinEngine:
    """
    达尔文进化引擎
    
    适用对象：
    - SKILL.md 文件
    - AI Agent prompt 文件
    - 产品配置文件
    - 任何有评估标准的文本资产
    
    使用方法：
        engine = DarwinEngine("~/my-project")
        report = engine.evolve("prompts/my-agent.md", max_rounds=3)
    """
    
    def __init__(self, project_path: str):
        self.project_path = os.path.expanduser(project_path)
        self.reports_dir = os.path.join(self.project_path, ".darwin")
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def score(self, asset_path: str) -> ScoreResult:
        """
        8维度评分
        
        这是Agent-B的工作：独立评估一个资产的质量
        返回结构化评分结果
        """
        full_path = os.path.join(self.project_path, asset_path)
        
        if not os.path.exists(full_path):
            return ScoreResult(total=0, notes=f"文件不存在: {asset_path}")
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        scores = {}
        total = 0
        
        # 1. Frontmatter规范性 (8分)
        fm_score = 0
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end > 0:
                fm = content[3:fm_end]
                if "name:" in fm: fm_score += 2
                if "description:" in fm and len(fm.split("description:")[1].split("\n")[0]) > 10:
                    fm_score += 2
                if "triggers:" in fm or "trigger:" in fm: fm_score += 2
                if "category:" in fm or "version:" in fm: fm_score += 2
        scores["frontmatter"] = {"score": fm_score, "max": 8}
        total += fm_score
        
        # 2. 工作流清晰度 (15分)
        wf_score = 0
        lines = content.split("\n")
        step_lines = [l for l in lines if l.strip().startswith(("##", "###", "Step", "步骤"))]
        if len(step_lines) >= 3: wf_score += 5
        if len(step_lines) >= 5: wf_score += 5
        # 检查有序列表
        numbered = [l for l in lines if l.strip() and l.strip()[0].isdigit() and "." in l[:4]]
        if len(numbered) >= 3: wf_score += 5
        wf_score = min(wf_score, 15)
        scores["workflow_clarity"] = {"score": wf_score, "max": 15}
        total += wf_score
        
        # 3. 异常处理 (10分)
        err_score = 0
        err_keywords = ["error", "异常", "失败", "fallback", "兜底", "边界", "如果", "if", "exception", "catch"]
        for kw in err_keywords:
            if kw.lower() in content.lower():
                err_score += 2
                if err_score >= 10: break
        scores["error_handling"] = {"score": err_score, "max": 10}
        total += err_score
        
        # 4. 确认检查点 (7分)
        cp_score = 0
        cp_keywords = ["确认", "confirm", "检查点", "checkpoint", "暂停", "wait", "用户", "please"]
        for kw in cp_keywords:
            if kw.lower() in content.lower():
                cp_score += 1
                if cp_score >= 7: break
        scores["checkpoints"] = {"score": cp_score, "max": 7}
        total += cp_score
        
        # 5. 指令具体性 (15分)
        spec_score = 0
        if "```" in content: spec_score += 5  # 有代码块/示例
        if "示例" in content or "example" in content.lower(): spec_score += 5
        if "格式" in content or "format" in content.lower(): spec_score += 3
        if len(content) > 1000: spec_score += 2  # 足够详细
        spec_score = min(spec_score, 15)
        scores["specificity"] = {"score": spec_score, "max": 15}
        total += spec_score
        
        # 6. 路径完整性 (5分)
        path_score = 5  # 默认满分，检查后扣分
        import re
        paths = re.findall(r'[~/.][\w/\-._]+', content)
        for p in paths[:5]:
            expanded = os.path.expanduser(p)
            if not os.path.exists(expanded):
                path_score = max(0, path_score - 2)
        scores["path_integrity"] = {"score": path_score, "max": 5}
        total += path_score
        
        # 7. 架构合理性 (15分)
        arch_score = 0
        if len(step_lines) > 0: arch_score += 5
        if "---" in content: arch_score += 3  # 有分隔
        if len(content.split("\n\n")) >= 4: arch_score += 4  # 段落结构
        if len(content) < 5000: arch_score += 3  # 简洁
        arch_score = min(arch_score, 15)
        scores["architecture"] = {"score": arch_score, "max": 15}
        total += arch_score
        
        # 8. 实测输出质量 (25分) — 需要真实测试，默认给基线
        # 实际使用时由Agent-B或人工评估
        scores["real_world_output"] = {"score": 0, "max": 25, "note": "需要实测评估"}
        
        return ScoreResult(
            total=total,
            dimensions=scores,
            timestamp=datetime.now().isoformat(),
            scorer="agent-b-auto",
        )
    
    def find_weakest_dimension(self, score: ScoreResult) -> str:
        """找到得分率最低的维度"""
        weakest = ""
        lowest_rate = 1.0
        
        for dim_name, dim_data in score.dimensions.items():
            max_s = SCORING_DIMENSIONS[dim_name]["max_score"]
            rate = dim_data["score"] / max_s if max_s > 0 else 1.0
            if rate < lowest_rate:
                lowest_rate = rate
                weakest = dim_name
        
        return weakest
    
    def _git(self, *args) -> str:
        """执行git命令"""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.project_path,
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            return f"git error: {e}"
    
    def _get_current_commit(self) -> str:
        return self._git("rev-parse", "HEAD")
    
    def evolve_plan(self, asset_path: str) -> dict:
        """
        生成进化计划
        
        这是Agent-A的工作：分析当前状态，提出改进方向
        """
        score = self.score(asset_path)
        weakest = self.find_weakest_dimension(score)
        dim_info = SCORING_DIMENSIONS[weakest]
        
        return {
            "asset": asset_path,
            "current_score": score.total,
            "weakest_dimension": weakest,
            "weakest_name": dim_info["name"],
            "current_dim_score": score.dimensions.get(weakest, {}).get("score", 0),
            "max_dim_score": dim_info["max_score"],
            "improvement_checks": dim_info["checks"],
            "suggestion": f"重点改进「{dim_info['name']}」维度（当前 {score.dimensions.get(weakest, {}).get('score', 0)}/{dim_info['max_score']}分）",
        }
    
    def save_report(self, report: EvolutionReport):
        """保存进化报告"""
        report_path = os.path.join(
            self.reports_dir,
            f"evolution-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        return report_path


# ============================================
# 项目扫描器 — 找到所有可进化资产
# ============================================

EVOLVABLE_PATTERNS = [
    "SKILL.md",
    "*.prompt.md",
    "PROMPT.md",
    "agent_config.yaml",
    "agent_config.json",
    "system_prompt.txt",
]


def scan_evolvable_assets(project_path: str) -> list:
    """
    扫描项目中所有可进化的资产
    
    返回：[{"path": "relative/path", "type": "skill|prompt|config", "size": 1234}]
    """
    project_path = os.path.expanduser(project_path)
    assets = []
    
    for root, dirs, files in os.walk(project_path):
        # 跳过隐藏目录和node_modules等
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".git")]
        
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, project_path)
            
            # SKILL.md
            if f == "SKILL.md":
                assets.append({"path": rel_path, "type": "skill", "size": os.path.getsize(full_path)})
            
            # Prompt files
            elif f.endswith(".prompt.md") or f == "PROMPT.md":
                assets.append({"path": rel_path, "type": "prompt", "size": os.path.getsize(full_path)})
            
            # Config files with agent/prompt content
            elif f in ("agent_config.yaml", "agent_config.json", "system_prompt.txt"):
                assets.append({"path": rel_path, "type": "config", "size": os.path.getsize(full_path)})
    
    return assets


def batch_score(project_path: str) -> dict:
    """
    批量评分 — 对项目中所有可进化资产评分
    
    返回：
    {
        "assets": [...],
        "summary": {"total": 10, "avg_score": 65, "weakest": "xxx"},
        "ranking": [...]  # 按分数排序
    }
    """
    engine = DarwinEngine(project_path)
    assets = scan_evolvable_assets(project_path)
    
    results = []
    for asset in assets:
        score = engine.score(asset["path"])
        weakest = engine.find_weakest_dimension(score)
        results.append({
            "path": asset["path"],
            "type": asset["type"],
            "score": score.total,
            "weakest_dimension": weakest,
            "dimensions": score.dimensions,
        })
    
    # 按分数排序
    results.sort(key=lambda x: x["score"])
    
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    
    return {
        "project": project_path,
        "assets": results,
        "summary": {
            "total_assets": len(results),
            "avg_score": round(avg_score, 1),
            "lowest_score": results[0] if results else None,
            "highest_score": results[-1] if results else None,
        },
        "ranking": results,
    }


# ============================================
# CLI入口
# ============================================

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python darwin.py <command> [args]")
        print()
        print("命令:")
        print("  scan <project_path>              扫描可进化资产")
        print("  score <project_path> <asset>     单项评分")
        print("  batch <project_path>             批量评分")
        print("  plan <project_path> <asset>      生成进化计划")
        print()
        print("示例:")
        print("  python darwin.py scan ~/Desktop/metaforge")
        print("  python darwin.py score ~/Desktop/metaforge app/agents/seeker.py")
        print("  python darwin.py batch ~/Desktop/skills")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "scan":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        assets = scan_evolvable_assets(path)
        print(f"\n🔍 扫描 {path}")
        print(f"找到 {len(assets)} 个可进化资产:\n")
        for a in assets:
            print(f"  [{a['type']:8}] {a['path']} ({a['size']:,} bytes)")
    
    elif cmd == "score":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        asset = sys.argv[3] if len(sys.argv) > 3 else ""
        engine = DarwinEngine(path)
        result = engine.score(asset)
        print(f"\n📊 评分: {asset}")
        print(f"总分: {result.total}/100\n")
        for dim, data in result.dimensions.items():
            info = SCORING_DIMENSIONS[dim]
            bar = "█" * data["score"] + "░" * (info["max_score"] - data["score"])
            print(f"  {info['name']:12} {bar} {data['score']}/{info['max_score']}")
    
    elif cmd == "batch":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = batch_score(path)
        print(f"\n📊 批量评分: {path}")
        print(f"共 {result['summary']['total_assets']} 个资产，平均分: {result['summary']['avg_score']}\n")
        for r in result["ranking"]:
            emoji = "🟢" if r["score"] >= 70 else "🟡" if r["score"] >= 50 else "🔴"
            print(f"  {emoji} {r['score']:3d} {r['path']}")
    
    elif cmd == "plan":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        asset = sys.argv[3] if len(sys.argv) > 3 else ""
        engine = DarwinEngine(path)
        plan = engine.evolve_plan(asset)
        print(f"\n🧬 进化计划: {asset}")
        print(f"当前分数: {plan['current_score']}")
        print(f"最弱维度: {plan['weakest_name']} ({plan['current_dim_score']}/{plan['max_dim_score']})")
        print(f"建议: {plan['suggestion']}")
        print(f"改进方向:")
        for check in plan["improvement_checks"]:
            print(f"  • {check}")


if __name__ == "__main__":
    main()
