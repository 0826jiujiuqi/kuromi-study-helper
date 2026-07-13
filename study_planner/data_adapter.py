import json
from datetime import date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models import StudyPlanConfig, PlanTask

# 如果你原有打卡表的类名不是DailyRecord，替换成你实际的类名
try:
    from models import DailyRecord
except ImportError:
    # 无对应打卡表时使用默认值，不影响功能运行
    DailyRecord = None


class SQLAlchemyDataAdapter:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    # ========== 规划配置读写 ==========
    def save_config(self, config: Dict):
        # 单用户场景：先删旧配置再插入新的
        self.db.query(StudyPlanConfig).delete()
        db_config = StudyPlanConfig(
            sprint_start_date=config["sprint_start_date"],
            daily_study_hours=config["daily_study_hours"],
            subject_weights=json.dumps(config["subject_weights"], ensure_ascii=False),
            buffer_ratio=config.get("buffer_ratio", 0.1)
        )
        self.db.add(db_config)
        self.db.commit()

    def load_config(self) -> Optional[Dict]:
        db_config = self.db.query(StudyPlanConfig).first()
        if not db_config:
            return None
        return {
            "sprint_start_date": db_config.sprint_start_date,
            "daily_study_hours": db_config.daily_study_hours,
            "subject_weights": json.loads(db_config.subject_weights),
            "buffer_ratio": db_config.buffer_ratio
        }

    # ========== 任务库读写（替代原导入功能） ==========
    def save_task_library(self, tasks: List[Dict]):
        self.db.query(PlanTask).delete()
        for task in tasks:
            db_task = PlanTask(**task)
            self.db.add(db_task)
        self.db.commit()

    def load_task_library(self) -> List[Dict]:
        tasks = self.db.query(PlanTask).all()
        return [
            {
                "id": t.id,
                "subject": t.subject,
                "task_name": t.task_name,
                "total_amount": t.total_amount,
                "unit": t.unit,
                "unit_size": t.unit_size,
                "unit_hours": t.unit_hours
            }
            for t in tasks
        ]

    # ========== 对接你原有的打卡数据 ==========
    def get_recent_records(self, days: int = 3) -> List[Dict]:
        if not DailyRecord:
            return [{"completion_rate": 1.0, "status_score": 4.0, "weak_points": []}]

        records = self.db.query(DailyRecord).order_by(DailyRecord.date.desc()).limit(days).all()
        records.reverse()
        result = []
        for r in records:
            result.append({
                "date": r.date.isoformat() if hasattr(r.date, 'isoformat') else str(r.date),
                "completion_rate": getattr(r, 'completion_rate', 1.0),
                "status_score": getattr(r, 'status_score', 4.0),
                "weak_points": json.loads(r.weak_points) if getattr(r, 'weak_points', None) else []
            })
        return result if result else [{"completion_rate": 1.0, "status_score": 4.0, "weak_points": []}]
