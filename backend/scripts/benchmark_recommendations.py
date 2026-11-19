"""Workload cố định, chỉ dữ liệu mẫu, không DB và không provider."""
import argparse,asyncio,json,statistics,sys,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument("--source",default=str(Path(__file__).resolve().parents[2]));args=parser.parse_args()
sys.path.insert(0,str(Path(args.source)/"backend"))
from app.services.recommender.service import calculate_3pillar_recommendations
from app.schemas.recommender import RecommendationRequest
async def run():
    profile={"riasec_answers":{f"{g}{i}":5 if g=="I" else 2 for g in "RIASEC" for i in range(1,6)},"grades_by_subject":{"Toán":8.125,"Vật lí":8.125,"Hóa học":8.125},"cognitive_preferences":{},"aspiration":{}}
    durations=[];count=0
    for index in range(6):
        start=time.perf_counter()
        result=await calculate_3pillar_recommendations(None,None,RecommendationRequest(top_k=15),profile,persist_history=False)
        elapsed=(time.perf_counter()-start)*1000
        if index: durations.append(round(elapsed,2))
        count=result.total_majors_evaluated
    print(json.dumps({"catalog_size":count,"warm_runs_ms":durations,"median_ms":statistics.median(durations),"mean_ms":round(statistics.mean(durations),2)}))
asyncio.run(run())
