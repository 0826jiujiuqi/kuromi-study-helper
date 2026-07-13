import os
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
CF_D1_DB_ID = os.environ.get("CF_D1_DB_ID")
SUBJECTS = ['数学','英语','专业课','政治']
EXAM_DATE = '2026-12-20'
DEFAULT_GOALS = {'数学':{'一轮结束':'2026-08-31','刷题开始':'2026-09-15'},'英语':{'一轮结束':'2026-08-20','刷题开始':'2026-09-01'},'专业课':{'一轮结束':'2026-09-10','刷题开始':'2026-09-20'},'政治':{'一轮结束':'2026-09-30','刷题开始':'2026-10-10'}}
ACTIVITY_WEIGHTS = {'新学':0.6,'复习':0.3,'做题':0.4,'看视频':0.2}
REVIEW_INTERVALS = [1,2,4,7,15]
