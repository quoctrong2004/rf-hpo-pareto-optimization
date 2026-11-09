# Dataset

Đồ án sử dụng **Breast Cancer Wisconsin (Diagnostic)** được tích hợp sẵn trong `scikit-learn` thông qua `sklearn.datasets.load_breast_cancer`.

- Số mẫu: 569.
- Số đặc trưng: 30 đặc trưng số.
- Bài toán: phân loại nhị phân.
- Nguồn dữ liệu trong chương trình: thư viện scikit-learn; không cần tải dữ liệu thủ công hoặc Internet khi chạy thí nghiệm.
- Quy trình chia: `train_test_split(test_size=0.20, stratify=y, random_state=42)`, tạo 455 mẫu development và 114 mẫu test.
- Test set được khóa trong toàn bộ quá trình tuning; chỉ mở ở giai đoạn đánh giá cuối cho các cấu hình đã được lựa chọn bằng CV.

Dataset là dữ liệu benchmark phục vụ học tập/nghiên cứu. Mô hình trong đồ án **không phải công cụ chẩn đoán y khoa** và không được dùng để đưa ra quyết định điều trị.

## Tái lập

Dùng phiên bản thư viện đã ghi trong `requirements.txt`, sau đó chạy `python run_project.py`. Mã nguồn tự tải dataset từ scikit-learn.
