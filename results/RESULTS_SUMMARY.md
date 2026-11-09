# Tóm tắt kết quả thực nghiệm

## HPO đơn mục tiêu (3 seeds, mỗi seed 24 trial, 5-fold CV)
- Grid Search: best CV accuracy = 0.9648 ± 0.0022; average wall time = 7.21 s.
- Optuna TPE: best CV accuracy = 0.9641 ± 0.0025; average wall time = 8.20 s.
- Random Search: best CV accuracy = 0.9648 ± 0.0022; average wall time = 6.99 s.

## NSGA-II
- Tổng trial: 20
- Số nghiệm Pareto: 7
- Nghiệm knee: trial 13, CV accuracy 0.9560, latency median 1.2629 ms, total nodes 552.

## Đánh giá cuối trên test set đã khóa
- Baseline mặc định: test accuracy = 0.9561; median latency = 5.8166 ms; total nodes = 3,556; model size = 0.309 MB.
- Best HPO (CV cao nhất): test accuracy = 0.9561; median latency = 2.4257 ms; total nodes = 1,392; model size = 0.122 MB.
- Pareto knee (NSGA-II): test accuracy = 0.9474; median latency = 1.2738 ms; total nodes = 552; model size = 0.051 MB.

Lưu ý: latency phụ thuộc máy chạy, hệ điều hành, tải nền và cách triển khai. Không xem latency đo trong đồ án là cam kết hiệu năng trên thiết bị khác.