import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    # Determine mode based on version
    mode = "dense" if "V1" in agent_version else "hybrid"
    
    agent = MainAgent(mode=mode)
    evaluator = RetrievalEvaluator()
    judge = LLMJudge()

    runner = BenchmarkRunner(agent, evaluator, judge)
    results = await runner.run_all(dataset)

    total = len(results)
    stats = {
        "score": sum(r["judge"]["final_score"] for r in results) / total,
        "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
        "judge_agreement": sum(r["judge"]["agreement_rate"] for r in results) / total
    }
    
    return results, stats

async def main():
    # V1 Baseline
    v1_results, v1_stats = await run_benchmark_with_results("Agent_V1_Baseline")
    
    # V2 Optimized
    v2_results, v2_stats = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if v1_stats is None or v2_stats is None:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    delta = v2_stats["score"] - v1_stats["score"]
    
    print(f"V1 Score: {v1_stats['score']:.2f}")
    print(f"V2 Score: {v2_stats['score']:.2f}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")

    os.makedirs("reports", exist_ok=True)
    
    # Build summary.json structure
    summary = {
        "metadata": {
            "total": len(v2_results),
            "version": "Agent_V2_Optimized",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "versions_compared": ["V1", "V2"]
        },
        "metrics": {
            "avg_score": v2_stats["score"],
            "hit_rate": v2_stats["hit_rate"],
            "agreement_rate": v2_stats["judge_agreement"]
        },
        "regression": {
            "v1": v1_stats,
            "v2": v2_stats,
            "decision": "APPROVE" if delta > 0 else "BLOCK"
        }
    }
    
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    combined_results = {
        "v1": v1_results,
        "v2": v2_results
    }
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(combined_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
