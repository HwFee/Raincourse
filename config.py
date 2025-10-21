# 答题提交间隔时间
DO_WORK_DURATION_SPAN = 1

DEEPSEEK_API_TOKEN = "sk-481c2e4d5ecd4ea5825fd4f5c78fe3cf"

# --- 1. 定义常量和初始化 ---
VIDEO_COMPLETION_THRESHOLD = 0.99  # 视频完成度的阈值
LEARNING_RATE = 4  # 每次心跳事件增加的视频帧数
HEARTBEAT_BATCH_SIZE = 3  # 每次请求发送的心跳事件数量
LOOP_SLEEP_INTERVAL = 2  # 每次循环后的常规等待时间（秒）
RETRY_SLEEP_INTERVAL = 5  # API请求失败后的重试等待时间（秒）

PPT_DURATION_SPAN = 1

QUESTION_TYPE = {
    "1": "单选题",
    "2": "多选题",
    "3": "判断题",
    "4": "填空题",
}

__VERSION__ = 'v1.0.4'