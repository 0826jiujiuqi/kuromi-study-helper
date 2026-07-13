from datetime import date, datetime, timedelta
from database import get_goals, get_events, get_nodes, save_daily_plan, get_plan, get_sleep_records, get_state_stats, get_states, get_tasks, get_knowledge_points
from estimator import estimate_mastery, compute_next_review, compute_subject_progress, get_subject_avg_mastery
from config import SUBJECTS, EXAM_DATE, REVIEW_INTERVALS
import numpy as np

class Planner:
    def __init__(self):
        self.goals={}
        for g in get_goals():
            self.goals[g.subject]={'one_round_end':g.one_round_end,'practice_start':g.practice_start,'current_phase':g.current_phase,'phase_start':g.phase_start,'phase_end':g.phase_end}
        if not self.goals:
            from config import DEFAULT_GOALS
            for sub,g in DEFAULT_GOALS.items():
                self.goals[sub]={'one_round_end':datetime.strptime(g['一轮结束'],'%Y-%m-%d').date(),'practice_start':datetime.strptime(g['刷题开始'],'%Y-%m-%d').date(),'current_phase':'','phase_start':None,'phase_end':None}
        self.today=date.today()
        self.exam_date=datetime.strptime(EXAM_DATE,'%Y-%m-%d').date()

    def generate_plan(self):
        events=get_events(90)
        if len(events)<5:
            return "⚠️ 数据不足（至少需要5条学习记录），请先记录学习事件或导入数据。", {}, [], []
        nodes=get_nodes()
        today=self.today
        status={}
        for sub in SUBJECTS:
            prog=compute_subject_progress(sub, events)
            avg_m=get_subject_avg_mastery(sub)
            one_end=self.goals.get(sub,{}).get('one_round_end')
            rem=(one_end-today).days if one_end else 30
            urgency=1.0
            if rem<=0: urgency=2.0
            else: urgency=1.0+(1.0-prog)*10/max(rem,1)
            last_plan=get_plan((today-timedelta(days=1)).isoformat())
            if last_plan and last_plan.completion_rate>0:
                urgency*=(1-last_plan.completion_rate*0.3)
            status[sub]={'progress':prog,'mastery':avg_m,'remaining':rem,'urgency':urgency}
        avg_daily=self._estimate_avg_duration(events)
        base=max(240,min(600,avg_daily))
        total_u=sum(s['urgency'] for s in status.values()) or 1
        alloc={sub:int(base*status[sub]['urgency']/total_u) for sub in SUBJECTS}
        due_reviews=[n for n in nodes if n.next_review and n.next_review<=today]
        due_reviews.sort(key=lambda n:n.next_review)
        weak_nodes=[n for n in nodes if n.mastery<0.5]
        weak_nodes.sort(key=lambda n:n.mastery)

        # ---- 任务分析 ----
        all_tasks=get_tasks()
        task_groups={}
        for t in all_tasks:
            key=(t.subject,t.phase)
            if key not in task_groups:
                task_groups[key]={'total':0,'completed':0,'pending':[]}
            task_groups[key]['total']+=1
            if t.status=='已完成':
                task_groups[key]['completed']+=1
            else:
                task_groups[key]['pending'].append(t)
        today_events=[e for e in events if e.date==today]
        today_pending=[]
        for t in all_tasks:
            if t.status!='已完成' and t.plan_date<=today:
                today_pending.append(t)

        # ---- 知识点分析 ----
        all_kps=get_knowledge_points()
        kp_stats={}
        if all_kps:
            for sub in SUBJECTS:
                sub_kps=[k for k in all_kps if k.subject==sub]
                total=len(sub_kps)
                learned=len([k for k in sub_kps if k.status in ['已学','掌握']])
                unlearned=total-learned
                kp_stats[sub]={'total':total,'learned':learned,'unlearned':unlearned}
            for sub, goal in self.goals.items():
                practice_start=goal.get('practice_start')
                if practice_start:
                    days_until=(practice_start-today).days
                    if days_until>0:
                        daily_need=max(1, int(kp_stats.get(sub,{}).get('unlearned',0)/days_until))
                    else:
                        daily_need=0
                else:
                    daily_need=0
                if sub in kp_stats:
                    kp_stats[sub]['daily_need']=daily_need

        # ---- 构建计划文本 ----
        lines=[]
        lines.append("📅 今日详细学习计划")
        lines.append(f"预计总时长：{sum(alloc.values())} 分钟\n")
        for sub,dur in alloc.items():
            line=f"{sub}: {dur}分钟"
            if status[sub]['remaining']<0: line+=" ⚠️ 已超一轮截止"
            elif status[sub]['remaining']<7: line+=" 🔥 即将到期"
            lines.append(line)

        # 任务进度
        lines.append("\n📋 任务进度与明日建议：")
        if task_groups:
            for (sub,phase), info in task_groups.items():
                progress=info['completed']/info['total']*100 if info['total']>0 else 0
                lines.append(f"{sub} - {phase}: 完成 {info['completed']}/{info['total']} ({progress:.1f}%)")
                if info['pending']:
                    pending_desc=[t.description for t in info['pending'][:3]]
                    lines.append(f"  剩余任务：{', '.join(pending_desc)}")
                    if sub in alloc:
                        alloc[sub]=int(alloc[sub]*1.2)
        else:
            lines.append("  暂无任务，请先添加阶段任务。")
        if today_pending:
            lines.append("\n⚠️ 以下任务已过期或今日到期，建议明日优先完成：")
            for t in today_pending[:5]:
                lines.append(f"  • {t.subject} - {t.description} (计划完成: {t.plan_date})")
        else:
            lines.append("\n✅ 今日无到期未完成任务。")
        if today_events and today_pending:
            lines.append("\n📌 今日已学习，但仍有计划任务未完成，明日应优先补上。")
        elif today_events and not today_pending:
            lines.append("\n📌 今日已完成学习，任务进度良好，继续保持。")
        elif not today_events and today_pending:
            lines.append("\n📌 今日尚未学习，请尽快开始，否则任务可能无法按期完成。")

        # 知识点进度
        if all_kps:
            lines.append("\n📚 基于资料的知识点进度：")
            for sub, stats in kp_stats.items():
                lines.append(f"{sub}: 总{stats['total']}，已学{stats['learned']}，未学{stats['unlearned']}")
                if stats.get('daily_need',0)>0:
                    lines.append(f"  建议每日学习 {stats['daily_need']} 个新知识点以确保按时进入冲刺")
            unlearned_kps=[k for k in all_kps if k.status=='未学']
            if unlearned_kps:
                unlearned_kps.sort(key=lambda k:(k.priority,k.importance), reverse=True)
                lines.append("\n🎯 明日建议学习的新知识点：")
                for sub, stats in kp_stats.items():
                    daily=stats.get('daily_need',0)
                    if daily>0:
                        kps_sub=[k for k in unlearned_kps if k.subject==sub][:daily]
                        if kps_sub:
                            lines.append(f"{sub}（需学{daily}个）：")
                            for k in kps_sub:
                                lines.append(f"  • {k.title}")
            else:
                lines.append("\n✅ 所有知识点已学完，可进入冲刺刷题阶段。")
        else:
            lines.append("\n📚 暂无知识点资料，请导入各科知识点清单。")

        # 复习和薄弱点
        if due_reviews:
            lines.append("\n🔔 今日必须复习的知识点：")
            for n in due_reviews[:5]:
                lines.append(f"  • {n.subject} - {n.topic} (掌握度 {n.mastery:.2f})，上次复习 {n.last_review}")
            if len(due_reviews)>5:
                lines.append(f"  还有 {len(due_reviews)-5} 个知识点待复习")
        else:
            lines.append("\n✅ 今日无到期复习知识点")
        if weak_nodes:
            lines.append("\n🎯 薄弱知识点攻坚（建议优先）：")
            for n in weak_nodes[:5]:
                prereq=n.prereq
                prereq_node=next((x for x in nodes if x.topic==prereq), None) if prereq else None
                if prereq_node and prereq_node.mastery<0.5:
                    lines.append(f"  • {n.subject} - {n.topic} (掌握度 {n.mastery:.2f}) ⚠️ 先修 '{prereq}' 未掌握，请先复习先修！")
                else:
                    lines.append(f"  • {n.subject} - {n.topic} (掌握度 {n.mastery:.2f})，建议分配 {int(alloc.get(n.subject,0)*0.2)} 分钟专门复习")
        else:
            lines.append("\n✅ 无特别薄弱知识点，可综合刷题")

        # 阶段诊断、效率、睡眠
        phase_advice=self._evaluate_phase()
        if phase_advice: lines.append("\n📌 阶段规划诊断：\n"+phase_advice)
        eff_advice=self._analyze_efficiency()
        if eff_advice: lines.append("\n⏳ 效率时段分析：\n"+eff_advice)
        sleep_advice=self._sleep_advice()
        if sleep_advice: lines.append("\n😴 睡眠优化建议：\n"+sleep_advice)

        plan_text="\n".join(lines)
        save_daily_plan(today.isoformat(), plan_text)
        return plan_text, alloc, due_reviews, weak_nodes

    def _estimate_avg_duration(self, events):
        recent=[e for e in events if (self.today-e.date).days<=7]
        if not recent: return 360
        total=sum(e.duration for e in recent)
        days=len(set(e.date for e in recent))
        return total/days if days else 360

    def _sleep_advice(self):
        records=get_sleep_records(30)
        if len(records)<3: return "数据不足，建议保持7-8小时睡眠。"
        data=[]
        for rec in records:
            bed=datetime.combine(self.today, rec.bed_time)
            wake=datetime.combine(self.today, rec.wake_time)
            if wake<=bed: wake+=timedelta(days=1)
            sleep_min=(wake-bed).seconds//60
            if rec.efficiency>0: data.append((sleep_min, rec.efficiency))
        if not data: return "暂无效率数据，建议保持7小时睡眠。"
        data.sort(key=lambda x:x[1], reverse=True)
        top_n=max(1, int(len(data)*0.3))
        best_avg=np.mean([d[0] for d in data[:top_n]])
        last_rec=records[-1]
        bed_today=datetime.combine(self.today, last_rec.bed_time)
        if bed_today>datetime.now(): bed_today-=timedelta(days=1)
        wake_time=bed_today+timedelta(minutes=int(best_avg))
        wake_str=wake_time.strftime('%H:%M')
        return f"最佳睡眠时长约{int(best_avg)}分钟，建议闹钟设为{wake_str}。"

    def _evaluate_phase(self):
        advice=""
        for sub, goal in self.goals.items():
            phase=goal.get('current_phase','')
            p_start=goal.get('phase_start')
            p_end=goal.get('phase_end')
            if not phase: continue
            if p_start and p_end:
                if self.today<p_start: advice+=f"⚠️ {sub}阶段'{phase}'尚未开始（开始于{p_start}），请勿提前。\n"
                elif self.today>p_end: advice+=f"⚠️ {sub}阶段'{phase}'已超期（原定{p_end}），请调整或加速。\n"
            if self.today>=goal['practice_start'] and compute_subject_progress(sub)<0.8:
                advice+=f"⚠️ {sub}已进入刷题期但一轮进度仅{compute_subject_progress(sub)*100:.0f}%，建议暂停刷题，补一轮。\n"
        if not advice: advice="✅ 当前阶段规划合理，进度正常。"
        return advice

    def _analyze_efficiency(self):
        stats=get_state_stats(30)
        if not stats or not stats.get('hourly'): return "暂无足够状态数据，建议多汇报状态以便分析。"
        hourly=stats['hourly']
        if not hourly: return "暂无时段数据。"
        from collections import defaultdict
        hour_pos=defaultdict(int); hour_neg=defaultdict(int)
        states=get_states(30)
        for s in states:
            h=s.datetime.hour
            if s.state in ['高效','正常']: hour_pos[h]+=1
            else: hour_neg[h]+=1
        ratios={}
        for h in set(hour_pos.keys())|set(hour_neg.keys()):
            total=hour_pos.get(h,0)+hour_neg.get(h,0)
            if total>0: ratios[h]=hour_pos.get(h,0)/total
        if not ratios: return "数据不足。"
        best_hour=max(ratios, key=ratios.get)
        worst_hour=min(ratios, key=ratios.get)
        advice=f"根据近30天状态统计，你效率最高的时段在 {best_hour}:00 左右，建议安排重要科目学习。\n"
        advice+=f"效率最低的时段在 {worst_hour}:00 左右，建议安排轻松任务或休息。"
        now_hour=datetime.now().hour
        if now_hour in ratios and ratios[now_hour]<0.4:
            advice+="\n⚠️ 当前时段你历史上效率偏低，建议先休息5分钟或换一个简单科目。"
        return advice
def get_sleep_recommendations(bed_time_str, nap_start_str, nap_duration):
    from database import get_sleep_records
    records=get_sleep_records(30)
    if len(records)<3: return None
    sleep_data=[]
    for rec in records:
        bed=datetime.combine(date.today(), rec.bed_time)
        wake=datetime.combine(date.today(), rec.wake_time)
        if wake<=bed: wake+=timedelta(days=1)
        sleep_min=(wake-bed).seconds//60
        if rec.efficiency>0: sleep_data.append((sleep_min, rec.efficiency))
    if sleep_data:
        sleep_data.sort(key=lambda x:x[1], reverse=True)
        top_n=max(1,int(len(sleep_data)*0.3))
        best_sleep=int(np.mean([d[0] for d in sleep_data[:top_n]]))
    else:
        best_sleep=420
    nap_data=[]
    for rec in records:
        if rec.nap_duration>0 and rec.efficiency>0:
            nap_data.append((rec.nap_duration, rec.efficiency))
    if nap_data:
        nap_data.sort(key=lambda x:x[1], reverse=True)
        top_n=max(1,int(len(nap_data)*0.3))
        best_nap=int(np.mean([d[0] for d in nap_data[:top_n]]))
    else:
        best_nap=30
    bed_dt=datetime.strptime(bed_time_str,'%H:%M')
    wake_dt=bed_dt+timedelta(minutes=best_sleep)
    wake_rec=wake_dt.strftime('%H:%M')
    nap_start_dt=datetime.strptime(nap_start_str,'%H:%M')
    nap_end_dt=nap_start_dt+timedelta(minutes=best_nap)
    nap_end_rec=nap_end_dt.strftime('%H:%M')
    return wake_rec, nap_end_rec