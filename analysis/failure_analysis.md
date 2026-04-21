# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 50
- **Tỉ lệ Pass/Fail:** 45/5
- **Điểm RAGAS trung bình:**
    - Faithfulness: 0.99
    - Relevancy: 0.98
- **Điểm LLM-Judge trung bình:** 4.31 / 5.0

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| Policy Hallucination | 3 | Agent cho phép các hành động vi phạm bảo mật (chia sẻ mật khẩu, mượn máy ngoài). |
| Retrieval Noise | 1 | Hybrid search đưa các thông tin chung chung lên trên quy định cụ thể. |
| Incomplete Policy | 1 | Agent không tìm thấy đoạn văn bản về Contractor trong context hẹp. |

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: Chia sẻ mật khẩu tài khoản Level 1
1. **Symptom:** Agent trả lời "Có thể chia sẻ" nếu chỉ trong 1 giờ.
2. **Why 1:** LLM bị đánh lừa bởi tính "tạm thời" và "Level 1" (Read only).
3. **Why 2:** Context chứa các đoạn về "Chia sẻ tài liệu" làm LLM nhầm lẫn với "Chia sẻ tài khoản".
4. **Why 3:** Quy định cấm chia sẻ mật khẩu nằm ở một chunk khác không được ưu tiên hàng đầu.
5. **Root Cause:** System Prompt chưa đủ mạnh để ép Agent tuân thủ tuyệt đối các nguyên tắc bảo mật cơ bản (Zero Trust).

### Case #2: Mượn máy bạn làm việc khi mất laptop
1. **Symptom:** Agent khuyên có thể mượn tạm để không gián đoạn công việc.
2. **Why 1:** LLM ưu tiên tính "Helpful" (giúp người dùng làm việc) hơn tính "Security".
3. **Why 2:** Context về "Sử dụng thiết bị" không được truy xuất chính xác.
4. **Why 3:** Câu hỏi chứa từ "mượn máy" làm BM25 tìm đến các đoạn về "Mượn thiết bị từ phòng IT".
5. **Root Cause:** Retrieval bị nhiễu keyword ("mượn máy") dẫn đến lấy sai context quy định về thiết bị cá nhân.

### Case #3: Contractor yêu cầu quyền vĩnh viễn
1. **Symptom:** Agent trả lời là có thể nếu làm việc lâu năm.
2. **Why 1:** LLM suy luận sai dựa trên cụm từ "lâu năm".
3. **Why 2:** Context trả về chỉ nói về "Quyền truy cập" nói chung, không chứa đoạn "Contractor phải gia hạn hàng năm".
4. **Why 3:** Đoạn văn bản cụ thể về Contractor nằm xa đoạn về Policy chung.
5. **Root Cause:** Chunking strategy làm tách rời quy định chung và các trường hợp ngoại lệ (Contractor).

## 4. Kế hoạch cải tiến (Action Plan)
- [ ] Cập nhật System Prompt với bộ quy tắc "Security First" (Không bao giờ chia sẻ pass, không dùng máy ngoài).
- [ ] Thay đổi Chunking strategy sang Semantic Chunking để gom nhóm các quy định và ngoại lệ.
- [ ] Thêm bước Reranking vào Pipeline để ưu tiên các chunk có tính "Negative Policy" (Cấm/Không được phép).
