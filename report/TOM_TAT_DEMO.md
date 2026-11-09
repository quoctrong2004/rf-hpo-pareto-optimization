# TÓM TẮT DEMO - 5 ĐẾN 7 PHÚT

## 1. Mở đầu (30 giây)
Đồ án nghiên cứu cách tìm bộ siêu tham số phù hợp cho Random Forest và cách chọn mô hình khi cần cân bằng độ chính xác, tốc độ dự đoán và độ phức tạp. Dataset là Breast Cancer Wisconsin có sẵn trong scikit-learn, gồm 569 mẫu và 30 đặc trưng.

## 2. Mô hình hóa (60 giây)
Biến quyết định gồm `n_estimators`, `max_depth`, `min_samples_split`, `max_features`. Bài toán đơn mục tiêu tối đa hóa accuracy trung bình của 5-fold CV. Bài toán đa mục tiêu tối đa hóa accuracy, tối thiểu hóa latency và tổng số node của các cây.

## 3. Quy trình thực nghiệm (60 giây)
Dữ liệu được chia phân tầng 80% development, 20% test. Test set được khóa. Baseline Random Forest mặc định được đánh giá trước. Grid Search, Random Search và Optuna/TPE cùng dùng 24 trial cho mỗi seed, với ba seed 17, 42, 73. Sau đó NSGA-II chạy 20 trial để tạo tập nghiệm Pareto.

## 4. Kết quả (90 giây)
- Baseline CV accuracy: 0.9597 ± 0.0025.
- Grid Search: 0.9648 ± 0.0022.
- Random Search: 0.9648 ± 0.0022.
- Optuna/TPE: 0.9641 ± 0.0025.
- NSGA-II cho 6 nghiệm Pareto; nghiệm knee có CV accuracy 0.9560, median latency khoảng 0.947 ms/mẫu và 552 node.

Trên test set, baseline và best HPO cùng đạt accuracy 0.9561; best HPO giảm median latency từ khoảng 4.244 ms xuống 1.785 ms và giảm tổng node từ 3,556 xuống 1,392. Nghiệm Pareto knee đạt accuracy 0.9474 nhưng chỉ khoảng 0.970 ms và 552 node.

## 5. Quyết định (60 giây)
Nếu ưu tiên accuracy, chọn best HPO. Nếu thiết bị cần mô hình gọn và phản hồi nhanh, nghiệm knee là phương án hợp lý hơn, chấp nhận accuracy giảm nhẹ. Pareto front không tự chọn một mô hình; yêu cầu triển khai mới quyết định điểm nào phù hợp.

## 6. Hạn chế (30 giây)
Chỉ dùng một dataset benchmark, NSGA-II mới chạy 20 trial, latency đo trên một môi trường phần cứng và search space đơn mục tiêu có 24 cấu hình nhỏ. Đây là đồ án nhập môn, chưa phải hệ thống chẩn đoán y khoa hoặc benchmark triển khai thực tế.

---

## Câu hỏi giảng viên có thể hỏi

**1. Parameter và hyperparameter khác nhau thế nào?**  
Parameter là trọng số mô hình học từ dữ liệu; hyperparameter là lựa chọn bên ngoài như số cây, độ sâu cây và số mẫu tối thiểu để tách node.

**2. Vì sao không dùng test set trong objective?**  
Nếu dùng test để chọn tham số, mô hình sẽ gián tiếp thích nghi với test và kết quả cuối không còn khách quan. Vì vậy tuning dùng CV trên development set, test chỉ đánh giá cuối.

**3. Study và Trial trong Optuna khác nhau thế nào?**  
Study là toàn bộ chiến dịch tối ưu; Trial là một lần thử một cấu hình hyperparameter.

**4. Dominance là gì?**  
Một nghiệm dominate nghiệm khác khi nó không kém ở bất kỳ mục tiêu nào và tốt hơn ở ít nhất một mục tiêu.

**5. Vì sao best accuracy chưa chắc là mô hình cuối?**  
Vì mô hình có accuracy cao hơn có thể chậm hơn, lớn hơn hoặc tiêu tốn tài nguyên hơn. Cần nhìn các trade-off và bối cảnh triển khai.

**6. Tại sao Grid và Random cho kết quả bằng nhau?**  
Miền Grid chỉ có đúng 24 cấu hình và Random cũng lấy đủ 24 cấu hình, nên Random đã lấy hết tập cấu hình đó, chỉ khác thứ tự.

**7. Vì sao không dùng pruning?**  
Mỗi trial Random Forest trong thí nghiệm này chỉ có một kết quả CV cuối, không có metric trung gian theo epoch để pruner so sánh và dừng sớm có cơ sở.
