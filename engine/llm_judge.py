import asyncio
import os
import json
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMJudge:
    def __init__(self, model_a: str = "gpt-4o", model_b: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_a = model_a
        self.model_b = model_b
        
        # Persona 1: Strict & Factual
        self.persona_a = """
Bạn là một Giám khảo Khắt khe (Strict Expert). 
Tiêu chí của bạn: 
- Chỉ chấp nhận thông tin chính xác 100% so với Ground Truth.
- Trừ điểm nặng nếu thiếu các con số, ngày tháng hoặc thực thể quan trọng.
- Không chấp nhận các câu trả lời chung chung.
"""

        # Persona 2: Helpful & Contextual
        self.persona_b = """
Bạn là một Giám khảo Thấu cảm (Helpful Assistant). 
Tiêu chí của bạn:
- Đánh giá xem câu trả lời có giúp ích cho người dùng không.
- Nếu câu trả lời đúng ý chính nhưng diễn đạt khác Ground Truth, bạn vẫn có thể cho điểm cao.
- Ưu tiên sự rõ ràng và tính ứng dụng của câu trả lời.
"""

        self.rubrics = """
Chấm điểm câu trả lời dựa trên Ground Truth (GT) theo thang điểm 1-5:
1: Sai hoàn toàn hoặc không liên quan.
2: Có ý đúng nhưng thiếu sót nghiêm trọng hoặc có lỗi sai thông tin.
3: Trả lời được ý chính nhưng thiếu chi tiết hoặc cách diễn đạt chưa tốt.
4: Trả lời chính xác, đầy đủ hầu hết các ý, hành văn tốt.
5: Trả lời xuất sắc, hoàn toàn chính xác và chuyên nghiệp.

Trả về kết quả dưới định dạng JSON: {"score": <int>, "reasoning": "<string>"}
"""

    async def _call_judge(self, model: str, persona: str, question: str, answer: str, ground_truth: str) -> Dict:
        prompt = f"""
{persona}

Hãy đánh giá câu trả lời của Agent dựa trên câu hỏi và đáp án chuẩn (Ground Truth).

Câu hỏi: {question}
Đáp án chuẩn (GT): {ground_truth}
Câu trả lời của Agent: {answer}

{self.rubrics}
"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=[{"role": "system", "content": "You are a professional AI evaluator."},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"score": 0, "reasoning": f"Error OpenAI ({model}): {str(e)}"}

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        Gọi 2 Judge OpenAI với 2 tính cách khác nhau.
        """
        task_a = self._call_judge(self.model_a, self.persona_a, question, answer, ground_truth)
        task_b = self._call_judge(self.model_b, self.persona_b, question, answer, ground_truth)
        
        results = await asyncio.gather(task_a, task_b)
        res_a, res_b = results
        
        score_a = res_a.get("score", 0)
        score_b = res_b.get("score", 0)
        
        avg_score = (score_a + score_b) / 2
        agreement = 1.0 if score_a == score_b else 0.5
        status = "consensus" if abs(score_a - score_b) <= 1 else "conflict"

        return {
            "final_score": avg_score,
            "agreement_rate": agreement,
            "individual_results": {
                f"{self.model_a}-strict": res_a,
                f"{self.model_b}-helpful": res_b
            },
            "status": status
        }

if __name__ == "__main__":
    async def test():
        judge = LLMJudge()
        res = await judge.evaluate_multi_judge(
            "Định nghĩa P1?", 
            "P1 là sự cố nghiêm trọng nhất.", 
            "P1 là sự cố mức độ ưu tiên cao nhất, cần xử lý ngay trong 1h."
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
