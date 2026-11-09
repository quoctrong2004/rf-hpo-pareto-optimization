# Random Forest HPO & Pareto Optimization

**Đồ án cá nhân - Môn Nhập môn Tối ưu hóa**  
Trường Đại học Văn Lang - Khoa Công nghệ thông tin  
Sinh viên: **Dương Quốc Trọng** | MSSV: **2274802010932**

## 1. Bài toán

Đồ án khảo sát cách lựa chọn siêu tham số cho mô hình Random Forest trên bộ dữ liệu Breast Cancer Wisconsin (Diagnostic). Điểm chính không nằm ở việc xây một ứng dụng AI, mà ở việc mô hình hóa và giải quyết bài toán tối ưu:

- **Decision variables:** `n_estimators`, `max_depth`, `min_samples_split`, `max_features`.
- **Single objective:** maximize mean accuracy trên 5-fold cross-validation.
- **Multi-objective:** maximize CV accuracy, minimize inference latency và minimize tổng số node của các cây.
- **Baseline:** RandomForestClassifier với cấu hình mặc định.
- **Phương pháp:** Grid Search, Random Search, Optuna/TPE và NSGA-II.
- **Ràng buộc thực nghiệm:** cùng dataset, cùng cách chia, cùng metric, cùng số trial, cùng 5-fold CV; test set được khóa cho đến đánh giá cuối.

## 2. Kết quả chính đã chạy

### So sánh HPO đơn mục tiêu

Mỗi phương pháp có 24 trial/seed, lặp với 3 seed (17, 42, 73), dùng cùng 5-fold CV. Tổng cộng mỗi phương pháp có 72 evaluations.

| Phương pháp | Best CV accuracy trung bình | Độ lệch chuẩn giữa 3 seed | Thời gian tìm kiếm trung bình/seed |
|---|---:|---:|---:|
| Grid Search | 0.9648 | 0.0022 | 6.11 s |
| Random Search | 0.9648 | 0.0022 | 6.32 s |
| Optuna TPE | 0.9641 | 0.0025 | 7.36 s |

Với search space hữu hạn chỉ có đúng 24 cấu hình và Random Search cũng lấy đủ 24 cấu hình, Random Search thực tế đã duyệt cùng tập ứng viên như Grid Search (chỉ khác thứ tự). Vì vậy hai phương pháp có cùng kết quả là điều dễ giải thích, không phải bằng chứng rằng Random Search luôn tương đương Grid Search. TPE có thể lấy lại một cấu hình đã thử trong ngân sách nhỏ, nên kết quả trung bình ở thí nghiệm này thấp hơn đôi chút.

### Đánh giá cuối trên test set đã khóa

| Mô hình | Test accuracy | Median latency (ms/mẫu) | Tổng node | Dung lượng model (MB) |
|---|---:|---:|---:|---:|
| Baseline mặc định | 0.9561 | 4.2436 | 3,556 | 0.309 |
| Best HPO (CV cao nhất) | 0.9561 | 1.7849 | 1,392 | 0.122 |
| Pareto knee (NSGA-II) | 0.9474 | 0.9695 | 552 | 0.051 |

NSGA-II chạy 20 trial và tìm được 6 nghiệm Pareto trong lần chạy này. Nghiệm knee được chọn bằng khoảng cách tới điểm lý tưởng sau khi chuẩn hóa ba mục tiêu. Cấu hình này có accuracy thấp hơn một chút nhưng nhanh và gọn hơn rõ rệt.

> Latency phụ thuộc phần cứng, hệ điều hành và tải nền. Số đo trong bảng chỉ mô tả môi trường chạy thí nghiệm, không phải cam kết cho thiết bị khác.

## 3. Cấu trúc repository

```text
rf-hpo-pareto-project/
├── README.md
├── requirements.txt
├── run_project.py
├── create_report.py            # Tạo lại báo cáo Word từ kết quả thực nghiệm
├── setup_windows.bat
├── run_windows.bat
├── .gitignore
├── src/
│   └── experiment.py          # Toàn bộ quy trình HPO + Pareto
├── notebooks/
│   └── 01_hpo_pareto_walkthrough.ipynb
├── data/
│   └── README.md              # Nguồn và cách lấy dữ liệu
├── results/
│   ├── baseline_cv.csv
│   ├── cv_search_history.csv
│   ├── search_seed_summary.csv
│   ├── search_method_summary.csv
│   ├── nsga2_all_trials.csv
│   ├── pareto_front.csv
│   ├── nsga2_study.db
│   ├── final_model_metrics.csv
│   ├── run_metadata.json
│   └── RESULTS_SUMMARY.md
├── figures/
│   ├── 01_best_so_far.png
│   ├── 02_pareto_accuracy_latency.png
│   ├── 03_pareto_accuracy_complexity.png
│   └── 04_method_comparison.png
├── models/
│   ├── baseline.joblib
│   ├── best_hpo.joblib
│   └── final_pareto_model.joblib
└── report/
    ├── Bao_cao_do_an_Nhap_mon_Toi_uu_hoa.docx
    └── TOM_TAT_DEMO.md
```

## 4. Cài đặt và chạy trên Windows

Yêu cầu Python 3.11 trở lên.

**Cách nhanh:** mở thư mục dự án, nhấp đúp `setup_windows.bat` để tạo môi trường ảo và cài thư viện. Sau đó nhấp đúp `run_windows.bat` để chạy lại toàn bộ thí nghiệm.

**Cách chạy bằng Terminal / PowerShell:**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_project.py
```

Sau khi chạy thành công, kiểm tra `results/` và `figures/`. Khi cần tạo lại báo cáo Word từ các tệp kết quả, chạy `python create_report.py`. Notebook có thể mở bằng Jupyter:

```powershell
jupyter notebook
```

Mở `notebooks/01_hpo_pareto_walkthrough.ipynb` để xem bảng kết quả và biểu đồ.

## 5. Hướng dẫn đọc kết quả

- `cv_search_history.csv`: từng trial, tham số, accuracy CV, độ lệch chuẩn fold, thời gian và best-so-far.
- `search_seed_summary.csv`: cấu hình tốt nhất của từng phương pháp ở từng seed.
- `search_method_summary.csv`: so sánh tổng hợp Grid, Random và TPE.
- `nsga2_all_trials.csv`: toàn bộ 20 trial đa mục tiêu.
- `pareto_front.csv`: các nghiệm non-dominated.
- `nsga2_study.db`: SQLite storage của Optuna Study, có thể mở bằng DB Browser for SQLite.
- `final_model_metrics.csv`: đánh giá các mô hình đã chốt trên test set và số đo triển khai.

## 6. Mô hình hóa ngắn gọn

Với vector hyperparameter \(x\), HPO đơn mục tiêu giải:

\[
\max_x \; \frac{1}{K}\sum_{k=1}^{K} Accuracy_k(x), \quad K=5.
\]

Bài toán đa mục tiêu giải:

\[
\max_x Accuracy_{CV}(x), \qquad \min_x Latency(x), \qquad \min_x Nodes(x).
\]

Trong đó `Nodes` là tổng số node của tất cả cây, được dùng làm proxy cho độ phức tạp. Nghiệm Pareto là nghiệm không bị nghiệm khác dominate trên cả ba mục tiêu.

## 7. Lưu ý về phạm vi và hạn chế

1. Dataset benchmark chỉ có 569 mẫu và một lần hold-out test; kết quả không đại diện cho dữ liệu lâm sàng hoặc hệ thống thực tế.
2. Search space đơn mục tiêu được giữ ở 24 cấu hình để giới hạn chi phí chạy trên máy cá nhân. `n_estimators` dùng 20/40/60 cây; các miền lớn hơn (ví dụ 100-800) có thể được khảo sát ở nghiên cứu tiếp theo.
3. NSGA-II có 20 trial nên Pareto front là kết quả xấp xỉ ban đầu, không khẳng định đã tìm được toàn bộ nghiệm tối ưu toàn cục.
4. Latency được đo cho batch một mẫu trên môi trường chạy hiện tại; cần benchmark lại trên thiết bị triển khai thật.
5. Không dùng pruning trong thí nghiệm này vì mỗi trial Random Forest chỉ tạo metric CV cuối, không có learning curve/intermediate metric theo epoch để pruner sử dụng.

## 8. AI assistance

AI được dùng để hỗ trợ tạo khung mã, giải thích thuật toán và biên tập tài liệu. Sinh viên cần tự chạy lại chương trình, kiểm tra phiên bản thư viện, hiểu từng biến quyết định, hàm mục tiêu, các ràng buộc và chịu trách nhiệm về kết quả khi bảo vệ.

## 9. Đưa dự án lên GitHub

Repository hiện được đóng gói ở dạng local ZIP; chưa được xuất bản lên tài khoản GitHub cá nhân. Để đáp ứng yêu cầu public của học phần: tạo repository public tên `rf-hpo-pareto-optimization`, giải nén bộ dự án vào repository, commit theo các checkpoint thực tế của 5 tuần, rồi bổ sung URL GitHub vào báo cáo và README. Không ghi URL giả khi repository chưa được tạo.

## 10. Tài liệu môn học sử dụng

- `TAI_LIEU_CHUONG_6_Hyperparameter_Multiobjective_AI.pdf` - Chương 6, đặc biệt các mục 6.1-6.15, case study Random Forest và bài thực hành tự học.
- `HUONG_DAN_PHAM_VI_DE_BAI_TAP_LON_GITHUB_PORTFOLIO.pdf` - phạm vi xanh, tiêu chí baseline, ngân sách, protocol và GitHub Portfolio.
- `DE_BAI_TAP_LON_CA_NHAN_5_TUAN_GITHUB_PORTFOLIO.pdf` - nhiệm vụ, sản phẩm phải nộp, tiến độ 5 tuần và rubric.
