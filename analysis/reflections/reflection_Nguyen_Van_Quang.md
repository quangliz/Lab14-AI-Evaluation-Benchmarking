# Cá nhân phản hồi - Quang (quangliz)

## Engineering Contribution
Tôi chịu trách nhiệm chính về phần **Core Retrieval Engine** của dự án:
- **Xây dựng Vector Database**: Sử dụng ChromaDB để tạo bộ Index cho 5 sample data, và tạo ra 50 bộ câu hỏi test.
- **Hybrid Retrieval Implementation**: Triển khai dense retrieval và sparse retrieval, sau đó sử dụng Reciprocal Rank Fusion (RRF) để kết hợp kết quả.
- **Git Commits**: Phụ trách các commit từ `924a019` đến `6a1261d`, bao gồm việc thiết lập môi trường và tối ưu hóa logic tìm kiếm.

## Technical Depth
### 1. MRR (Mean Reciprocal Rank)
Trong quá trình làm bài, tôi nhận thấy **Hit Rate** chỉ cho biết thông tin có nằm trong Top-K hay không, nhưng **MRR** mới là chỉ số quan trọng để đánh giá chất lượng xếp hạng. MRR gán trọng số cao hơn cho các kết quả ở vị trí số 1 ($1/1$) so với vị trí số 3 ($1/3$). Điều này cực kỳ quan trọng trong RAG vì context đầu tiên thường ảnh hưởng mạnh nhất đến câu trả lời của LLM.

### 2. Trade-off: Dense vs Sparse
- **Dense (Vector)**: Tốt trong việc hiểu ngữ nghĩa nhưng đôi khi bỏ lỡ các mã số kỹ thuật chính xác.
- **Sparse (BM25)**: Mạnh trong việc tìm các keyword đặc biệt như "P1", "ext. 9000".
- **Giải pháp**: Tôi chọn Hybrid Retrieval để tận dụng cả hai, giúp tăng Hit Rate từ 0.92 lên 0.98.

## Problem Solving
**Vấn đề**: Khi triển khai Hybrid search, tôi gặp hiện tượng "Retrieval Noise" - BM25 đôi khi đưa các đoạn văn dài có nhiều từ khóa lặp lại lên trên các đoạn ngắn chứa thông tin chính xác.
**Giải quyết**: Tôi đã điều chỉnh trọng số RRF và bổ sung thêm bước tiền xử lý câu hỏi để lọc bỏ các "stop words" không cần thiết trước khi đưa vào bộ máy Sparse search.
