import os
import json
import time
import re 
from core.agent import AIAgent
from core.io_manager import IOManager
from config import BASE_PROJECT_PATH, COMPANY_VAULT_PATH
from typing import Any, Dict, List, Tuple, Optional

# ============================================================
# KOTA KORUMA İÇİN AKILLI BEKLEME
# ============================================================
def safe_api_call(func, *args, **kwargs):
    retries = 3
    wait = 15 

    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "503" in err_str:
                match = re.search(r"retry in ([0-9.]+)\s*s", err_str)
                wait = int(float(match.group(1))) + 2 if match else wait * 2
                print(f"\n⚠️ API Limitine takıldık! {wait} saniye bekleniyor... (Deneme {attempt+1})")
                time.sleep(wait)
            else:
                raise e
    return None

# ============================================================
# ROBUST JSON PARSING WITH VALIDATION
# ============================================================
def clean_json_string(raw: str) -> str:
    """Robustly extract and clean JSON from API responses."""
    if not raw:
        return ""
    
    raw = raw.strip()
    
    # Remove markdown code blocks
    if raw.startswith("```"):
        parts = raw.split("\n", 1)
        raw = parts[-1] if len(parts) > 1 else ""
    if raw.endswith("```"):
        raw = raw.rsplit("\n", 1)[0]
    
    raw = raw.strip()
    
    # Find first JSON bracket
    for i, c in enumerate(raw):
        if c in ["[", "{"]:
            raw = raw[i:]
            break
    
    return raw.strip()


def parse_json_safe(json_string: str, default: Any = None) -> Any:
    """Parse JSON with comprehensive error handling and recovery."""
    if not json_string or not json_string.strip():
        return default
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        # Try to fix common JSON issues
        try:
            # Remove trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', json_string)
            # Replace single quotes with double quotes (basic approach)
            fixed = fixed.replace("'", '"')
            return json.loads(fixed)
        except:
            pass
        
        # If all else fails, return default
        return default


def validate_json_structure(data: Any, expected_type: type = dict) -> bool:
    """Validate that parsed JSON matches expected structure."""
    if expected_type == dict and not isinstance(data, dict):
        return False
    if expected_type == list and not isinstance(data, list):
        return False
    return True


def _extract_detective_conclusion(detective_text: str, initial_request: str = None, log_func=None) -> Dict[str, Any]:
    """
    Extract single detective conclusion from JSON or text.
    Returns a dict with suspect, weapon, location, motive, evidence.
    """
    if not detective_text or not detective_text.strip():
        return {"suspect": "Bilinmiyor", "weapon": "Bilinmiyor", "location": "Bilinmiyor", "motive": "Bilinmiyor"}

    def find_with_regex(text, patterns):
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def normalize_candidate(name):
        if not name:
            return name
        return name.strip().strip('"\'').strip()

    def extract_suspects_from_input(text):
        suspects = []
        if not text:
            return suspects
        for line in text.splitlines():
            if line.strip().upper().startswith("SUSPECTS:") or line.strip().upper().startswith("ŞÜPHELİLER:"):
                values = line.split(":", 1)[1].strip()
                suspects.extend([s.strip() for s in re.split(r"[,;]", values) if s.strip()])
            elif line.strip().upper().startswith("SUSPECT:") or line.strip().upper().startswith("ŞÜPHELİ:"):
                values = line.split(":", 1)[1].strip()
                suspects.extend([s.strip() for s in re.split(r"[,;]", values) if s.strip()])
        return suspects

    conditions = ["bilinmiyor", "unknown", "not sure", "cannot determine", "uncertain"]

    # Try JSON first
    json_str = clean_json_string(detective_text)
    parsed = parse_json_safe(json_str)
    if isinstance(parsed, dict):
        conclusion = {
            "suspect": parsed.get("suspect", "Bilinmiyor"),
            "weapon": parsed.get("weapon", "Bilinmiyor"),
            "location": parsed.get("location", "Bilinmiyor"),
            "motive": parsed.get("motive", "Bilinmiyor"),
            "evidence": parsed.get("evidence", ""),
            "logic": parsed.get("logic", ""),
            "confidence": parsed.get("confidence", 0.7)
        }
        if conclusion["suspect"] and conclusion["suspect"].lower() not in conditions:
            return conclusion

    # Fallback: extract from text
    conclusion = {
        "suspect": "Bilinmiyor",
        "weapon": "Bilinmiyor",
        "location": "Bilinmiyor",
        "motive": "Bilinmiyor",
        "analysis": detective_text[:300]
    }

    # Key extraction patterns
    suspect_patterns = [
        r"(?:suspect|şüpheli|culprit|katil|guilty)[:\s]+([A-ZÇĞİÖŞÜ][A-Za-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*)",
        r"(?:the culprit is|katil (?:ol(?:du)?|tarafında)|suçlu(?:nun)?|şüpheli(?:nin)?)\s+([A-ZÇĞİÖŞÜ][A-Za-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*)",
        r"([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s+(?:was the culprit|committed the crime|did it|is guilty)",
        r"it was\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)",
        r"(?:the murderer is|katil)\s+([A-ZÇĞİÖŞÜ][A-Za-zçğıöşü]+)"
    ]
    weapon_patterns = [
        r"(?:weapon|silah)[:\s]+([A-Za-zÇĞİÖŞÜçğıöşü ]+)",
        r"used\s+the\s+([A-Za-zÇĞİÖŞÜçğıöşü ]+)"
    ]
    location_patterns = [
        r"(?:location|room|oda|yer)[:\s]+([A-Za-zÇĞİÖŞÜçğıöşü ]+)",
        r"in the\s+([A-Za-zÇĞİÖŞÜçğıöşü ]+)",
        r"at the\s+([A-Za-zÇĞİÖŞÜçğıöşü ]+)"
    ]
    motive_patterns = [
        r"(?:motive|motif)[:\s]+([A-Za-zÇĞİÖŞÜçğıöşü ]+)",
        r"because\s+([A-Za-zÇĞİÖŞÜçğıöşü ]+)"
    ]

    for line in detective_text.splitlines():
        if not conclusion["suspect"] or conclusion["suspect"] in conditions:
            suspect_candidate = find_with_regex(line, suspect_patterns)
            if suspect_candidate:
                conclusion["suspect"] = normalize_candidate(suspect_candidate)
        if not conclusion["weapon"] or conclusion["weapon"] in conditions:
            weapon_candidate = find_with_regex(line, weapon_patterns)
            if weapon_candidate:
                conclusion["weapon"] = normalize_candidate(weapon_candidate)
        if not conclusion["location"] or conclusion["location"] in conditions:
            location_candidate = find_with_regex(line, location_patterns)
            if location_candidate:
                conclusion["location"] = normalize_candidate(location_candidate)
        if not conclusion["motive"] or conclusion["motive"] in conditions:
            motive_candidate = find_with_regex(line, motive_patterns)
            if motive_candidate:
                conclusion["motive"] = normalize_candidate(motive_candidate)

    if conclusion["suspect"] in conditions or not conclusion["suspect"]:
        suspects = extract_suspects_from_input(initial_request) if initial_request else []
        for suspect_name in suspects:
            if suspect_name and suspect_name.lower() in detective_text.lower():
                conclusion["suspect"] = suspect_name
                break

    if conclusion["suspect"] in conditions or not conclusion["suspect"]:
        # As last resort, prefer first capitalized name in the detective text
        capitalized = re.findall(r"\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*)\b", detective_text)
        if capitalized:
            conclusion["suspect"] = capitalized[0]

    if log_func:
        log_func(f"✓ Dedektif sonucu çıkartıldı: {conclusion['suspect']}")

    return conclusion

def load_input(path=None):
    if path is None:
        path = input("Input file path (Enter = input.txt): ").strip()
        if not path:
            path = "input.txt"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return "Bilinmeyen Vaka", "", {}
    
    content = open(path, "r", encoding="utf-8").read()
    lines = content.splitlines()
    
    # Ground truth'u çıkar (eğer varsa)
    ground_truth = {}
    for i, line in enumerate(lines):
        if "GROUND TRUTH" in line or "ground_truth" in line.lower():
            # Satırı parse et: # GROUND TRUTH: {"culprit": "...", ...}
            try:
                json_start = line.find('{')
                if json_start != -1:
                    json_str = line[json_start:]
                    ground_truth = json.loads(json_str)
            except:
                pass
    
    if "project_name:" not in content:
        project_name = lines[0].strip() if lines else "Cinayet Vakası"
        customer_wish = content
        return project_name, customer_wish, ground_truth

    project_name = ""
    customer_wish = ""
    for line in lines:
        if line.startswith("project_name:"):
            project_name = line.split(":", 1)[1].strip()
        elif line.startswith("customer_wish:"):
            customer_wish = line.split(":", 1)[1].strip()

    return project_name, customer_wish, ground_truth

# ============================================================
# MAIN PIPELINE (SINGLE VS MULTI-AGENT DEBATE)
# ============================================================
def run_sdlc_simulation(
    project_name,
    initial_request,
    on_log=None,
    on_agent_status=None,
    on_task_progress=None,
    on_tasks_updated=None,
    on_ask_user=None,
):

    def log(msg):
        if on_log: on_log(msg)
        else: print(msg)

    def set_status(agent_key, status):
        if on_agent_status: on_agent_status(agent_key, status)

    def task_progress(agent, idx, total, task_id):
        if on_task_progress: on_task_progress(agent, idx, total, task_id)

    def tasks_updated(tasks):
        if on_tasks_updated: on_tasks_updated(tasks)

    def log_agent_output(agent_name, raw_text):
        if not raw_text or not raw_text.strip():
            log(f"[{agent_name} OUTPUT] (empty)")
            return
        log(f"\n[{agent_name} OUTPUT]\n{raw_text.strip()}\n")

    log(f"\n=== YAPAY ZEKA DEDEKTİFLİK TESTİ ===")
    log(f"Vaka: {project_name}")

    io = IOManager()
    safe_folder_name = project_name.replace(" ", "_").replace(":", "")[:30]
    project_path = io.create_project_structure(safe_folder_name)

    # Ajan İsimleri ve Klasör Yolları Tamamen Senin VS Code'una Göre
    single_agent = AIAgent("Tekil Ajan (Baseline)", "agents/singledet_prompt.txt")
    detective_agent = AIAgent("Baş Dedektif", "agents/detective_prompt.txt")
    prosecutor_agent = AIAgent("Savcı", "agents/prosecutor_prompt.txt")
    lawyer_agent = AIAgent("Savunma Avukatı", "agents/lawyer_prompt.txt")
    judge_agent = AIAgent("Yargıç", "agents/judge_prompt.txt")

    company_context = ""
    start_time = time.time()
    single_latency = 0

    # ========================================================================
    # AŞAMA 1: SINGLE-AGENT (Tek Ajan - Baseline Çözümü)
    # ========================================================================
    log("\n[AŞAMA 1: Single-Agent Baseline]")
    log("Tekil ajan vaka analizi yapıyor...")
    set_status("orchestrator", "active") 
    
    t0_single = time.time()
    single_input = f"VAKA DOSYASI:\n{initial_request}"
    single_agent_report = safe_api_call(single_agent.execute_task, single_input, company_context)
    single_latency = round(time.time() - t0_single, 1)
    
    io.write_file(f"{project_path}/01_single_agent_result.txt", single_agent_report)
    log_agent_output("Single-Agent", single_agent_report)
    set_status("orchestrator", "done")
    log(f"✔ Single-Agent tamamlandı ({single_latency} sn)")

    # ========================================================================
    # AŞAMA 2: DETECTIVE (Detektif Analizi - İpuçları Çıkarım)
    # ========================================================================
    log("\n[AŞAMA 2: Detektif Analizi]")
    log("Baş dedektif ipuçlarını analiz ediyor...")
    set_status("detective", "active") 
    
    t0_detective = time.time()
    detective_raw = safe_api_call(detective_agent.execute_task, single_input, company_context)
    detective_latency = round(time.time() - t0_detective, 1)
    
    if not detective_raw or detective_raw.strip() == "":
        log("❌ Detektif yanıt veremedi. Sistem durduruluyor.")
        return {"pass": 0, "fail": 0, "total": 1, "project_path": project_path}
    
    io.write_file(f"{project_path}/02_detective_raw.txt", detective_raw)
    log_agent_output("Detective", detective_raw)

    # Parse detective output
    detective_conclusion = _extract_detective_conclusion(detective_raw, initial_request, log)
    
    if not detective_conclusion.get('suspect') or detective_conclusion.get('suspect') == 'Bilinmiyor':
        log("❌ Detektif suçluyu belirleyemedi. Sistem durduruluyor.")
        return {"pass": 0, "fail": 0, "total": 1, "project_path": project_path}

    io.write_file(f"{project_path}/02_detective_conclusion.json", json.dumps(detective_conclusion, indent=2, ensure_ascii=False))
    set_status("detective", "done")
    log(f"✔ Detektif kararı: {detective_conclusion.get('suspect')} ({detective_latency} sn)")

    # ========================================================================
    # AŞAMA 3: SAVCΙ-AVUKAT TARTIŞMASI (2-3 Tur)
    # ========================================================================
    log("\n[AŞAMA 3: Mahkeme Tartışması]")
    
    prosecution_history = []
    defense_history = []
    
    # Tartışma turu (2-3 kez)
    debate_rounds = 2
    
    for round_num in range(1, debate_rounds + 1):
        log(f"\n>>> TARTIŞMA TURU {round_num}")
        
        # SAVCı SALDIRISI
        set_status("prosecutor", "active")
        log(f"  [Savcı] Detektif sonucuna saldırıyor...")
        
        t0_pros = time.time()
        
        if round_num == 1:
            # İlk tur: Detektif sonucundan başla
            prosecutor_input = f"VAKA DOSYASI:\n{initial_request}\n\nDETEKTİF SONUCU:\n{json.dumps(detective_conclusion, indent=2, ensure_ascii=False)}"
        else:
            # Sonraki turlar: Önceki savunmadan devam et
            prosecutor_input = f"VAKA DOSYASI:\n{initial_request}\n\nDETEKTİF SONUCU:\n{json.dumps(detective_conclusion, indent=2, ensure_ascii=False)}\n\nAVUKATIN ÖNCEKİ SAVUNMASI:\n{defense_history[-1]}"
        
        prosecutor_raw = safe_api_call(prosecutor_agent.execute_task, prosecutor_input, company_context)
        prosecutor_latency = round(time.time() - t0_pros, 1)
        
        prosecution_history.append(prosecutor_raw)
        io.write_file(f"{project_path}/03a_prosecutor_round{round_num}.txt", prosecutor_raw)
        log_agent_output(f"Prosecutor Round {round_num}", prosecutor_raw)
        set_status("prosecutor", "done")
        log(f"  ✔ Savcı saldırısı ({prosecutor_latency} sn)")
        
        # AVUKAT SAVUNMASI
        set_status("lawyer", "active")
        log(f"  [Avukat] Savcı saldırısına karşı savunuyor...")
        
        t0_law = time.time()
        lawyer_input = prosecutor_input + f"\n\nSAVCININ SALDIRISI:\n{prosecutor_raw}"
        lawyer_raw = safe_api_call(lawyer_agent.execute_task, lawyer_input, company_context)
        lawyer_latency = round(time.time() - t0_law, 1)
        
        defense_history.append(lawyer_raw)
        io.write_file(f"{project_path}/03b_lawyer_round{round_num}.txt", lawyer_raw)
        log_agent_output(f"Lawyer Round {round_num}", lawyer_raw)
        set_status("lawyer", "done")
        log(f"  ✔ Avukat savunması ({lawyer_latency} sn)")
    
    log(f"\n✔ {debate_rounds} tur tartışma tamamlandı")

    # ========================================================================
    # AŞAMA 4: JUDGE (Yargıç - Nihai Karar)
    # ========================================================================
    log("\n[AŞAMA 4: Yargıç Kararı]")
    log("Yargıç tüm kanıtları inceleyip nihai kararı veriyor...")
    set_status("judge", "active")
    
    t0_judge = time.time()
    
    # Tüm tartışma tarihçesini yargıca sun
    judge_input = f"""VAKA DOSYASI:
{initial_request}

DETEKTİF SONUCU:
{json.dumps(detective_conclusion, indent=2, ensure_ascii=False)}

SAVCININ SALDIRISILARI:
{chr(10).join([f'Tur {i+1}:{prose}' for i, prose in enumerate(prosecution_history)])}

AVUKATTIN SAVUNMALARI:
{chr(10).join([f'Tur {i+1}:{defense}' for i, defense in enumerate(defense_history)])}
"""
    
    judge_raw = safe_api_call(judge_agent.execute_task, judge_input, company_context)
    judge_latency = round(time.time() - t0_judge, 1)
    log_agent_output("Judge", judge_raw)
    
    # Parse judge decision with text fallback
    judge_json_str = clean_json_string(judge_raw)
    judge_decision = parse_json_safe(judge_json_str)
    if not isinstance(judge_decision, dict):
        judge_decision = {}
    
    if not judge_decision.get("verdict"):
        judge_text = judge_raw.lower()
        if "not guilty" in judge_text or "not_guilty" in judge_text or "insufficient evidence" in judge_text or "beraat" in judge_text or "aklan" in judge_text:
            judge_decision["verdict"] = "NOT_GUILTY"
        elif "guilty" in judge_text or "suçlu" in judge_text or "convicted" in judge_text:
            judge_decision["verdict"] = "GUILTY"
        else:
            judge_decision["verdict"] = "NOT_GUILTY"
        judge_decision["reasoning"] = judge_raw.strip()
    
    io.write_file(f"{project_path}/04_judge_verdict.json", json.dumps(judge_decision, indent=2, ensure_ascii=False))
    io.write_file(f"{project_path}/04_judge_raw_output.txt", judge_raw)
    set_status("judge", "done")
    
    final_verdict = judge_decision.get("verdict", "UNKNOWN")
    log(f"✔ Yargıç kararı: {final_verdict} ({judge_latency} sn)")

    # ========================================================================
    # SONUÇ ÖZETI
    # ========================================================================
    pass_count = 1 if final_verdict in ["GUILTY", "GÜNAHLı", "SUÇLU"] else 0
    fail_count = 1 - pass_count
    elapsed = round(time.time() - start_time, 1)

    log(
        f"\n{'='*70}\n"
        f" 📊 DOSYA ÖZET RAPORU\n"
        f"{'='*70}\n"
        f" [Single-Agent]    Çözüm Süresi: {single_latency} sn\n"
        f" [Detektif]        Analiz Süresi: {detective_latency} sn → {detective_conclusion.get('suspect')}\n"
        f" [Mahkeme]         {debate_rounds} tur tartışma yapıldı\n"
        f" [Yargıç]          Karar Süresi: {judge_latency} sn → {final_verdict}\n"
        f" [TOPLAM]          Toplam İşlem Süresi: {elapsed} sn\n"
        f"{'='*70}\n"
    )

    return {
        "pass": pass_count,
        "fail": fail_count,
        "total": 1,
        "project_path": project_path,
        "detective_conclusion": detective_conclusion,
        "judge_verdict": judge_decision
    }

if __name__ == "__main__":
    project_name, customer_wish, _ = load_input()
    print(f"Vaka: {project_name}")
    run_sdlc_simulation(project_name, customer_wish)