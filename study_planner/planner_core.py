import math
from datetime import date, timedelta
from typing import List, Dict
from .data_adapter import SQLAlchemyDataAdapter


class ReversePlanner:
    def __init__(self, data_adapter: SQLAlchemyDataAdapter = None):
        self.dm = data_adapter or SQLAlchemyDataAdapter()
        self.config = self.dm.load_config()
        self.tasks = self.dm.load_task_library()

    # 步骤1：计算时间维度参数
    def calculate_time_params(self) -> Dict:
        if not self.config:
            raise ValueError("请先完成规划配置")

        start_date = date.today()
        sprint_start = date.fromisoformat(self.config["sprint_start_date"])
        total_days = (sprint_start - start_date).days

        if total_days <= 0:
            raise ValueError("冲刺日期必须晚于今天")

        buffer_ratio = self.config.get("buffer_ratio", 0.1)
        buffer_days = math.ceil(total_days * buffer_ratio)
        valid_days = total_days - buffer_days
        total_weeks = math.ceil(valid_days / 7)

        # 三阶段划分：适应期40%、攻坚期40%、衔接期20%
        adapt_days = math.ceil(valid_days * 0.4)
        intense_days = math.ceil(valid_days * 0.4)
        connect_days = valid_days - adapt_days - intense_days

        return {
            "total_days": total_days,
            "buffer_days": buffer_days,
            "valid_days": valid_days,
            "total_weeks": total_weeks,
            "adapt_days": adapt_days,
            "intense_days": intense_days,
            "connect_days": connect_days,
            "sprint_start_date": sprint_start,
            "start_date": start_date
        }

    # 步骤2：量化各科总任务耗时
    def calculate_task_workload(self) -> Dict[str, float]:
        subject_workload = {}
        for task in self.tasks:
            subject = task["subject"]
            total_hours = task["total_amount"] * task["unit_hours"]
            if subject not in subject_workload:
                subject_workload[subject] = 0
            subject_workload[subject] += total_hours
        return subject_workload

    # 步骤3：按权重分配每日各科时长
    def allocate_daily_hours(self) -> Dict[str, float]:
        daily_total = self.config["daily_study_hours"]
        weights = self.config["subject_weights"]
        total_weight = sum(weights.values())

        daily_hours = {}
        for subject, weight in weights.items():
            daily_hours[subject] = round(daily_total * (weight / total_weight), 2)
        return daily_hours

    # 步骤4：生成全阶段基准日计划
    def generate_base_plan(self) -> List[Dict]:
        time_params = self.calculate_time_params()
        daily_hours = self.allocate_daily_hours()
        task_queues = self._build_task_queues()

        base_plan = []
        current_date = time_params["start_date"]
        valid_day_count = 0

        for day in range(time_params["total_days"]):
            # 每周日设为缓冲复盘日
            is_buffer = current_date.weekday() == 6
            if is_buffer:
                day_plan = {
                    "date": current_date.isoformat(),
                    "is_buffer": True,
                    "tasks": [{"subject": "复盘", "content": "本周进度复盘+错题整理+补进度", "duration": 2.0}]
                }
                base_plan.append(day_plan)
                current_date += timedelta(days=1)
                continue

            valid_day_count += 1
            # 阶段系数：适应期0.9，攻坚期1.1，衔接期0.8
            if valid_day_count <= time_params["adapt_days"]:
                phase_coeff = 0.9
            elif valid_day_count <= time_params["adapt_days"] + time_params["intense_days"]:
                phase_coeff = 1.1
            else:
                phase_coeff = 0.8

            day_tasks = []
            for subject, hours in daily_hours.items():
                adjusted_hours = hours * phase_coeff
                subject_tasks = self._take_tasks_for_hours(
                    task_queues.get(subject, []), adjusted_hours
                )
                day_tasks.extend(subject_tasks)

            # 加入固定复习时间
            review_hours = round(sum(t["duration"] for t in day_tasks) * 0.15, 1)
            day_tasks.append({
                "subject": "复盘复习",
                "content": "当日知识点回顾+前一日错题整理",
                "duration": review_hours
            })

            day_plan = {
                "date": current_date.isoformat(),
                "is_buffer": False,
                "phase_coeff": phase_coeff,
                "tasks": day_tasks,
                "total_hours": round(sum(t["duration"] for t in day_tasks), 1)
            }
            base_plan.append(day_plan)
            current_date += timedelta(days=1)

        return base_plan

    # 构建任务单元队列
    def _build_task_queues(self) -> Dict[str, List[Dict]]:
        queues = {}
        for task in self.tasks:
            subject = task["subject"]
            if subject not in queues:
                queues[subject] = []

            unit_size = task.get("unit_size", 1)
            total_units = math.ceil(task["total_amount"] / unit_size)

            for i in range(total_units):
                start = i * unit_size + 1
                end = min((i + 1) * unit_size, task["total_amount"])
                queues[subject].append({
                    "subject": subject,
                    "content": f"{task['task_name']} 第{start}-{end}{task['unit']}",
                    "duration": round(unit_size * task["unit_hours"], 2),
                    "task_id": task["id"]
                })
        return queues

    # 从队列中取出指定时长的任务
    def _take_tasks_for_hours(self, queue: List[Dict], target_hours: float) -> List[Dict]:
        taken = []
        current_hours = 0
        while queue and current_hours + queue[0]["duration"] <= target_hours * 1.1:
            task = queue.pop(0)
            taken.append(task)
            current_hours += task["duration"]
        return taken
