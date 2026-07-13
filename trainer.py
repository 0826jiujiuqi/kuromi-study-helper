import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from database import get_all_events, get_plan
from config import MODEL_DIR, EXAM_DATE
import os

MODEL_PATH = os.path.join(MODEL_DIR, 'capacity_predictor.pkl')

def train_model():
    events = get_all_events()
    if len(events) < 5:
        return
    df = pd.DataFrame([{'date': e.date, 'topic': e.topic, 'duration': e.duration} for e in events])
    daily = df.groupby('date').agg({'topic': 'count', 'duration': 'sum'}).reset_index()
    daily.columns = ['date', 'topic_count', 'total_duration']
    daily['dayofweek'] = pd.to_datetime(daily['date']).dt.dayofweek
    daily['prev_duration'] = daily['total_duration'].shift(1)
    daily['prev_topic_count'] = daily['topic_count'].shift(1)
    exam_date = pd.to_datetime(EXAM_DATE)
    daily['days_to_exam'] = (exam_date - pd.to_datetime(daily['date'])).dt.days
    daily['completion_rate'] = daily['date'].apply(lambda d: get_plan(d.isoformat()).completion_rate if get_plan(d.isoformat()) else 0.5)
    daily = daily.dropna()
    if len(daily) < 3:
        return
    X = daily[['dayofweek', 'prev_duration', 'prev_topic_count', 'days_to_exam', 'completion_rate']].values
    y = daily['topic_count'].values
    model = LinearRegression()
    model.fit(X, y)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

def predict_capacity(date_obj):
    if not os.path.exists(MODEL_PATH):
        return 5
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    events = get_all_events()
    if not events:
        return 5
    last = max(events, key=lambda e: e.date)
    prev_dur = last.duration
    prev_cnt = len([e for e in events if e.date == last.date])
    dow = date_obj.weekday()
    exam = datetime.strptime(EXAM_DATE, '%Y-%m-%d').date()
    d2e = (exam - date_obj).days
    plan = get_plan((date_obj - timedelta(days=1)).isoformat())
    comp = plan.completion_rate if plan else 0.5
    X = np.array([[dow, prev_dur, prev_cnt, d2e, comp]])
    pred = model.predict(X)
    return max(1, int(pred[0]))
