from datetime import date, timedelta
from database import get_events, get_nodes
import numpy as np
from config import ACTIVITY_WEIGHTS, REVIEW_INTERVALS

def estimate_mastery(topic, events=None):
    if events is None:
        events = get_events(90)
    node = next((n for n in get_nodes() if n.topic == topic), None)
    if not node:
        return 0.0
    topic_events = [e for e in events if e.topic == topic]
    if not topic_events:
        return 0.0
    mastery = 0.0
    today = date.today()
    for e in topic_events:
        days_ago = (today - e.date).days
        decay = np.exp(-days_ago / 14)
        weight = ACTIVITY_WEIGHTS.get(e.activity, 0.2)
        increment = (1 - mastery) * weight * 0.4 * decay
        mastery += increment
        if mastery > 1:
            mastery = 1
    return mastery

def compute_next_review(topic):
    node = next((n for n in get_nodes() if n.topic == topic), None)
    if not node or not node.last_review:
        return None
    base = node.last_review
    for interval in REVIEW_INTERVALS:
        candidate = base + timedelta(days=interval)
        if candidate > date.today():
            return candidate
    return base + timedelta(days=REVIEW_INTERVALS[-1])

def compute_subject_progress(subject, events=None):
    if events is None:
        events = get_events(365)
    all_topics = set([e.topic for e in events if e.subject == subject])
    if not all_topics:
        return 0.0
    learned = set([n.topic for n in get_nodes(subject) if n.mastery >= 0.5])
    return len(learned) / len(all_topics)

def get_subject_avg_mastery(subject):
    nodes = get_nodes(subject)
    if not nodes:
        return 0.0
    return np.mean([n.mastery for n in nodes])