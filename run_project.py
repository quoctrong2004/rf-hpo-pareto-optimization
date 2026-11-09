"""Điểm bắt đầu để chạy toàn bộ đồ án."""
from threadpoolctl import threadpool_limits
from src.experiment import run_experiments


if __name__ == "__main__":
    # Giới hạn thread để kết quả chạy ổn định hơn và tránh máy bị quá tải.
    with threadpool_limits(limits=1):
        run_experiments()
