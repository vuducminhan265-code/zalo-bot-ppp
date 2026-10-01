# Function department/tools/run_search.py
import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
func_dept_dir = os.path.dirname(current_dir)
if func_dept_dir not in sys.path:
    sys.path.insert(0, func_dept_dir)

from tools.web_search_grounding import WebSearchGrounder

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    log_file = os.path.join(func_dept_dir, "..", "scratch", "run_search_calls.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"INVOKED WITH QUERY: {query}\n")
    except Exception:
        pass

    grounder = WebSearchGrounder()
    res = grounder.ground_query(query)
    out = res.get("grounded_context", "Không tìm thấy dữ liệu tìm kiếm web.")
    print(out)
