# Cá nhân phản hồi - Dũng (dung323123)

## Engineering Contribution
Tôi chịu trách nhiệm về hệ thống **Evaluation Engine & Automation**:
- **Multi-Judge Consensus**: Thiết kế module `LLMJudge` sử dụng 2 Persona (Strict Expert & Helpful Assistant) để đánh giá chéo kết quả.
- **Regression Release Gate**: Viết logic so sánh V1 vs V2 trong `main.py` để tự động đưa ra quyết định "APPROVE" hoặc "BLOCK".
- **Git Commits**: Phụ trách các commit từ `cd8a0d0` đến `8475929`.

## Technical Depth
### 1. Position Bias & LLM Judges
Trong quá trình phát triển Multi-Judge, tôi đã nghiên cứu về **Position Bias** - hiện tượng LLM có xu hướng chấm điểm cao cho các câu trả lời dài hơn hoặc các câu trả lời nằm ở một vị trí nhất định trong Prompt. Để khắc phục, tôi đã sử dụng 2 Persona khác nhau và yêu cầu Judge đưa ra `reasoning` trước khi đưa ra `score` (Chain-of-Thought) để giảm thiểu bias này.

### 2. Trade-off: Cost vs Quality
Để tối ưu chi phí, tôi đề xuất sử dụng **GPT-4o-mini** cho các tác vụ tổng hợp câu trả lời của Agent, và chỉ sử dụng **GPT-4o** bản full cho bước Judge cuối cùng. Điều này giúp giảm 80% chi phí vận hành mà vẫn giữ được độ tin cậy của kết quả đánh giá.

## Problem Solving
**Vấn đề**: Khi chạy 50 cases, hệ thống thường xuyên bị lỗi `429 Rate Limit` từ phía OpenAI API.
**Giải quyết**: Tôi đã triển khai cơ chế **Batching** trong `runner.py`, chia 50 cases thành các đợt nhỏ (batch size = 5) và sử dụng `asyncio.sleep` giữa các đợt. Kết quả là pipeline chạy ổn định và hoàn thành trong ~120 giây mà không bị ngắt quãng.
