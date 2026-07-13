import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'en_US.UTF-8'
import json
from flask import render_template, request, redirect, url_for
from study_planner.data_adapter import SQLAlchemyDataAdapter
from study_planner.daily_adjuster import DailyTaskAdjuster
from flask import Flask, request, jsonify, render_template, make_response, Blueprint
from functools import wraps
from datetime import date, datetime
from models import db, KaoyanConfig, KaoyanDailyRecord
from models import Base, engine
from database import (
    add_event, get_events, get_all_events, get_nodes, get_plan,
    save_sleep, add_state, get_tasks, add_task, update_task_status, delete_task,
    get_knowledge_points, add_knowledge_points_bulk, delete_all_knowledge_points,
    parse_document, parse_knowledge_document, add_events_bulk,
    mark_plan_complete, clear_all_data, delete_event
)
from database import (
    get_all_study_records,
    get_all_sleep_records,
    get_all_daily_tasks,
    get_all_stage_tasks,
    get_all_status_reports
)
from planner import Planner
from trainer import train_model
import threading
from config import CF_ACCOUNT_ID, CF_API_TOKEN, CF_D1_DB_ID

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = f"d1://{CF_ACCOUNT_ID}:{CF_API_TOKEN}@{CF_D1_DB_ID}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

Base.metadata.create_all(engine)
with app.app_context():
    db.create_all()

plan_bp = Blueprint("plan", __name__, url_prefix="/plan")
USERNAME = os.environ.get('APP_USER', 'huayouque')
PASSWORD = os.environ.get('APP_PASS', 'chen2003')

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return ('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Kuromi Study Assistant"'})

@app.before_request
def before_request():
    if request.path.startswith('/static/'):
        return
    if request.path == '/favicon.ico':
        return
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

@app.teardown_appcontext
def shutdown_session(exception=None):
    from database import Session
    Session.remove()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/plan', methods=['GET'])
def get_plan_api():
    try:
        planner = Planner()
        plan_text, alloc, due_reviews, weak_nodes = planner.generate_plan()
        return jsonify({
            'status': 'success',
            'plan_text': plan_text,
            'alloc': alloc,
            'due_reviews': [{'subject': n.subject, 'topic': n.topic, 'mastery': n.mastery} for n in due_reviews[:5]],
            'weak_nodes': [{'subject': n.subject, 'topic': n.topic, 'mastery': n.mastery} for n in weak_nodes[:5]]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/event', methods=['POST'])
def post_event():
    data = request.json
    subject = data.get('subject')
    topic = data.get('topic')
    activity = data.get('activity')
    duration = data.get('duration')
    note = data.get('note', '')
    if not all([subject, topic, activity, duration]):
        return jsonify({'status': 'error', 'message': '缺少必要字段'}), 400
    try:
        add_event(subject, topic, activity, int(duration), note)
        return jsonify({'status': 'success', 'message': '学习记录已保存'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/mark_complete', methods=['POST'])
def mark_complete():
    data = request.json
    rate = data.get('rate', 1.0)
    today_str = date.today().isoformat()
    mark_plan_complete(today_str, True, float(rate))
    threading.Thread(target=train_model).start()
    return jsonify({'status': 'success', 'message': '今日计划已完成'})

@app.route('/api/sleep', methods=['POST'])
def post_sleep():
    data = request.json
    bed = data.get('bed_time')
    nap_start = data.get('nap_start')
    nap_dur = data.get('nap_duration')
    if not bed or not nap_start or not nap_dur:
        return jsonify({'status': 'error', 'message': '缺少字段'}), 400
    from planner import get_sleep_recommendations
    rec = get_sleep_recommendations(bed, nap_start, int(nap_dur))
    if rec:
        wake_rec, nap_end_rec = rec
    else:
        wake_rec = '06:30'
        nap_end_rec = '13:00'
    plan = get_plan(date.today().isoformat())
    eff = plan.completion_rate if plan else 0.0
    save_sleep(bed, wake_rec, int(nap_dur), eff)
    return jsonify({
        'status': 'success',
        'message': '睡眠记录已保存',
        'wake_recommend': wake_rec,
        'nap_end_recommend': nap_end_rec
    })

@app.route('/api/state', methods=['POST'])
def post_state():
    state = request.json.get('state')
    if not state:
        return jsonify({'status': 'error', 'message': '状态不能为空'}), 400
    advice = add_state(state)
    return jsonify({'status': 'success', 'message': '状态已记录', 'advice': advice})

@app.route('/history')
def history_page():
    study_list = get_all_study_records()
    sleep_list = get_all_sleep_records()
    daily_tasks = get_all_daily_tasks()
    stage_tasks = get_all_stage_tasks()
    status_list = get_all_status_reports()
    return render_template('history.html',
                           study_list=study_list,
                           sleep_list=sleep_list,
                           daily_tasks=daily_tasks,
                           stage_tasks=stage_tasks,
                           status_list=status_list)

@app.route('/api/event/<int:event_id>', methods=['DELETE'])
def delete_event_api():
    try:
        delete_event(event_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks_api():
    try:
        tasks = get_tasks()
        result = [{'id': t.id, 'subject': t.subject, 'phase': t.phase,
                   'description': t.description, 'plan_date': t.plan_date.isoformat(),
                   'status': t.status} for t in tasks]
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/task', methods=['POST'])
def add_task_api():
    data = request.json
    subject = data.get('subject')
    phase = data.get('phase')
    desc = data.get('description')
    plan_date = data.get('plan_date')
    if not all([subject, phase, desc, plan_date]):
        return jsonify({'status': 'error', 'message': '缺少字段'}), 400
    add_task(subject, phase, desc, plan_date)
    return jsonify({'status': 'success', 'message': '任务已添加'})

@app.route('/api/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    update_task_status(task_id, '已完成', date.today().isoformat())
    return jsonify({'status': 'success'})

@app.route('/api/task/<int:task_id>', methods=['DELETE'])
def delete_task_api():
    delete_task(task_id)
    return jsonify({'status': 'success'})

@app.route('/api/import_document', methods=['POST'])
def import_document():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '未上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '文件名为空'}), 400
    temp_path = os.path.join('/tmp', file.filename)
    file.save(temp_path)
    try:
        events = parse_document(temp_path)
        if not events:
            return jsonify({'status': 'error', 'message': '未解析到有效记录'}), 400
        add_events_bulk(events)
        return jsonify({'status': 'success', 'message': f'成功导入 {len(events)}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/api/import_knowledge', methods=['POST'])
def import_knowledge():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '未上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '文件名为空'}), 400
    temp_path = os.path.join('/tmp', file.filename)
    file.save(temp_path)
    try:
        kps = parse_knowledge_document(temp_path)
        if not kps:
            return jsonify({'status': 'error', 'message': '未解析到知识点'}), 400
        if request.form.get('replace', 'false') == 'true':
            delete_all_knowledge_points()
        add_knowledge_points_bulk(kps)
        return jsonify({'status': 'success', 'message': f'成功导入 {len(kps)}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/api/clear_all', methods=['POST'])
def clear_all():
    clear_all_data()
    return jsonify({'status': 'success', 'message': '所有数据已清空'})

@app.route('/api/train', methods=['POST'])
def train():
    threading.Thread(target=train_model).start()
    return jsonify({'status': 'success', 'message': '模型训练已启动'})

@app.route('/api/knowledge_points', methods=['GET'])
def get_kps():
    subject = request.args.get('subject')
    kps = get_knowledge_points(subject=subject)
    result = [{'id': k.id, 'subject': k.subject, 'title': k.title,
               'status': k.status, 'priority': k.priority} for k in kps]
    return jsonify(result)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

STANDARD_TASKS = {
    "英语一": [
        {"task_name": "大纲单词背诵", "total_amount": 5500, "unit": "个", "unit_size": 100, "unit_hours": 0.01, "subject": "英语"},
        {"task_name": "阅读真题一刷", "total_amount": 28, "unit": "篇", "unit_size": 2, "unit_hours": 0.75, "subject": "英语"},
        {"task_name": "翻译专项训练", "total_amount": 20, "unit": "句", "unit_size": 5, "unit_hours": 0.3, "subject": "英语"}
    ],
    "数学二": [
        {"task_name": "高数强化课程", "total_amount": 40, "unit": "讲", "unit_size": 2, "unit_hours": 0.75, "subject": "数学"},
        {"task_name": "660题高数部分", "total_amount": 400, "unit": "道", "unit_size": 20, "unit_hours": 0.05, "subject": "数学"},
        {"task_name": "线代强化课程", "total_amount": 20, "unit": "讲", "unit_hours": 0.75, "subject": "数学"},
        {"task_name": "880题线代部分", "total_amount": 200, "unit": "道", "unit_size": 20, "unit_hours": 0.06, "subject": "数学"}
    ],
    "政治": [
        {"task_name": "强化班课程", "total_amount": 50, "unit": "节", "unit_size": 2, "unit_hours": 0.5, "subject": "政治"},
        {"task_name": "1000题一刷", "total_amount": 1000, "unit": "道", "unit_size": 30, "unit_hours": 0.03, "subject": "政治"}
    ]
}

@app.route('/plan/init_db')
def init_plan_db():
    Base.metadata.create_all(bind=engine)
    with app.app_context():
        db.create_all()
    return "规划功能数据表创建成功！<a href='/plan/config'>前往配置</a>"

@plan_bp.route("/save_full_config", methods=["POST"])
def save_full_config():
    data = request.get_json()
    user_id = 1
    config = KaoyanConfig.query.filter_by(user_id=user_id).first()
    if not config:
        config = KaoyanConfig(user_id=user_id)
    config.subjects = data.get("subjects", "")
    config.sprint_date = data.get("sprint_date", "")
    config.daily_hour = data.get("daily_hour", 0)
    config.math_task = data.get("math_task", "")
    config.english_task = data.get("english_task", "")
    config.politics_task = data.get("politics_task", "")
    config.major_task = data.get("major_task", "")
    config.buffer_day = data.get("buffer_day", 1)
    config.time_prefer = data.get("time_prefer", "")
    config.weak_subject = data.get("weak_subject", "")
    db.session.add(config)
    db.session.commit()
    return jsonify({"success": True, "msg": "配置保存成功"})

@plan_bp.route("/api/get_daily_plan", methods=["GET"])
def get_daily_plan():
    user_id = 1
    today = datetime.now().strftime("%Y-%m-%d")
    config = KaoyanConfig.query.filter_by(user_id=user_id).first()
    if not config:
        return jsonify({
            "phase": "未配置备考规划",
            "finish_rate": "暂无学习数据",
            "strategy": "等待配置后自动生成",
            "weak_tip": "无重点补强方向",
            "task_list": []
        })
    now_date = datetime.now()
    sprint_date = datetime.strptime(config.sprint_date, "%Y-%m-%d") if config.sprint_date else None
    phase = ""
    strategy = ""
    if sprint_date and now_date < sprint_date:
        phase = "基础强化阶段"
        strategy = "平稳拆解任务，侧重知识点夯实与习题训练"
    else:
        phase = "真题冲刺阶段"
        strategy = "侧重整套模考、错题复盘、考点查漏补缺"
    weak_tip = config.weak_subject if config.weak_subject else "无重点补强方向"
    task_list = []
    if config.math_task:
        task_list.append({"subject":"数学","content":config.math_task,"standard":"完成当日拆解任务，整理错题"})
    if config.english_task:
        task_list.append({"subject":"英语","content":config.english_task,"standard":"完成刷题背诵，复盘长难句"})
    if config.politics_task:
        task_list.append({"subject":"政治","content":config.politics_task,"standard":"刷题背诵核心考点"})
    if config.major_task:
        task_list.append({"subject":"专业课","content":config.major_task,"standard":"梳理知识框架，完成训练"})
    record = KaoyanDailyRecord.query.filter_by(user_id=user_id, record_date=today).first()
    finish_rate = record.finish_rate if record else "暂无数据"
    return jsonify({
        "phase": phase,
        "finish_rate": finish_rate,
        "strategy": strategy,
        "weak_tip": weak_tip,
        "task_list": task_list
    })

@plan_bp.route("/api/submit_feedback", methods=["POST"])
def submit_feedback():
    user_id = 1
    data = request.get_json()
    feedback = data.get("feedback", "")
    today = datetime.now().strftime("%Y-%m-%d")
    record = KaoyanDailyRecord.query.filter_by(user_id=user_id, record_date=today).first()
    if not record:
        record = KaoyanDailyRecord(user_id=user_id, record_date=today)
    record.finish_rate = "95%"
    record.feedback = feedback
    db.session.add(record)
    db.session.commit()
    return jsonify({"success": True, "msg": "反馈提交成功"})

@plan_bp.route("/config")
def plan_config_html():
    return render_template("plan/config.html")

@plan_bp.route("/today")
def plan_today_html():
    return render_template("plan/today.html")

app.register_blueprint(plan_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
