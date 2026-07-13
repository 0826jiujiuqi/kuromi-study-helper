from datetime import date, timedelta
from typing import List, Dict
from .data_adapter import SQLAlchemyDataAdapter
from .planner_core import ReversePlanner


class DailyTaskAdjuster:
    def __init__(self, data_adapter: SQLAlchemyDataAdapter = None, planner: ReversePlanner = None):
        self.dm = data_adapter or SQLAlchemyDataAdapter()
        self.planner = planner or ReversePlanner(self.dm)
        self.base_plan = self.planner.generate_base_plan()

    # 获取今日基准任务
    def _get_today_base(self) -> Dict:
        today = date.today().isoformat()
        for day_plan in self.base_plan:
            if day_plan["date"] == today:
                return day_plan
        # 超出规划范围返回提示
        return {"date": today,
                "tasks": [{"subject": "提示", "content": "当前已进入冲刺阶段，请更新冲刺阶段任务", "duration": 0.5}],
                "is_buffer": False}

    # 计算近N天平均完成率
    def _calc_recent_completion_rate(self, days: int = 3) -> float:
        records = self.dm.get_recent_records(days)
        rates = [r.get("completion_rate", 1.0) for r in records]
        return sum(rates) / len(rates)

    # 获取昨日状态评分
    def _get_yesterday_status(self) -> float:
        records = self.dm.get_recent_records(1)
        if not records:
            return 4.0
        return records[0].get("status_score", 4.0)

    # 生成艾宾浩斯复习任务
    def _generate_review_tasks(self) -> List[Dict]:
        review_tasks = []
        today = date.today()
        memory_days = [1, 3, 7]

        for days_ago in memory_days:
            target_date = (today - timedelta(days=days_ago)).isoformat()
            for day_plan in self.base_plan:
                if day_plan["date"] == target_date and not day_plan["is_buffer"]:
                    review_tasks.append({
                        "subject": "复习回顾",
                        "content": f"{days_ago}天前学习内容复盘（艾宾浩斯记忆节点）",
                        "duration": 0.5
                    })
                    break
        return review_tasks

    # 生成调整后的今日任务
    def generate_today_tasks(self) -> Dict:
        base = self._get_today_base()
        if base["is_buffer"]:
            return base

        # 1. 基于完成率调整任务总量
        completion_rate = self._calc_recent_completion_rate()
        if completion_rate > 0.9:
            volume_coeff = 1.1
        elif completion_rate < 0.7:
            volume_coeff = 0.8
        else:
            volume_coeff = 1.0

        # 2. 基于状态调整任务强度
        status_score = self._get_yesterday_status()
        if status_score <= 3:
            status_coeff = 0.7
        elif status_score >= 4.5:
            status_coeff = 1.05
        else:
            status_coeff = 1.0

        total_coeff = round(volume_coeff * status_coeff, 2)

        # 应用调整系数
        adjusted_tasks = []
        for task in base["tasks"]:
            if task["subject"] == "复盘复习":
                adjusted_tasks.append(task)
                continue
            adjusted_task = task.copy()
            adjusted_task["duration"] = round(task["duration"] * total_coeff, 2)
            adjusted_tasks.append(adjusted_task)

        # 3. 加入记忆节点复习任务
        review_tasks = self._generate_review_tasks()
        adjusted_tasks.extend(review_tasks)

        # 4. 加入薄弱点专项训练
        weak_points = self._get_weak_points()
        if weak_points:
            adjusted_tasks.append({
                "subject": "专项强化",
                "content": f"薄弱点练习：{', '.join(weak_points)}",
                "duration": 0.5
            })

        total_hours = round(sum(t["duration"] for t in adjusted_tasks), 1)

        return {
            "date": base["date"],
            "total_hours": total_hours,
            "adjust_coeff": total_coeff,
            "completion_rate_3d": round(completion_rate, 2),
            "yesterday_status": status_score,
            "tasks": adjusted_tasks
        }

    # 获取近7天薄弱知识点
    def _get_weak_points(self) -> List[str]:
        records = self.dm.get_recent_records(7)
        weak = []
        for r in records:
            if "weak_points" in r:
                weak.extend(r["weak_points"])
        return list(set(weak))[:3]
