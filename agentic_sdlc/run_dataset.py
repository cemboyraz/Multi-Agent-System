import os
import time
import json
from main import run_sdlc_simulation, load_input
from dataset_analytics import DatasetAnalytics

def run_all_cases():
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        print(f"HATA: '{dataset_folder}' klasörü bulunamadı. Lütfen oluşturun.")
        return

    # Klasördeki tüm txt dosyalarını bul (alt klasörleri de kontrol et)
    case_files = []
    for root, dirs, files in os.walk(dataset_folder):
        for f in files:
            if f.endswith(".txt"):
                case_files.append(os.path.join(root, f))
    
    if not case_files:
        print("Dataset klasöründe hiç .txt dosyası yok!")
        return

    # SADECE İLK 3 CASE'İ TEST ET (çok fazla API çağrısını önlemek için)
    case_files = case_files[:3]
    
    print("="*60)
    print(f" VERİ SETİ TESTİ BAŞLIYOR ({len(case_files)} Vaka Seçildi)")
    print("="*60)

    results = []

    for index, filename in enumerate(case_files):
        filepath = os.path.join(dataset_folder, filename)
        project_name, customer_wish = load_input(filepath)
        
        print(f"\n[{index+1}/{len(case_files)}] Test Edilen Vaka: {project_name}")
        
        # main.py'deki sistemi tetikle (Logları ekrana basmasın diye lambda kullandık)
        result = run_sdlc_simulation(
            project_name=project_name,
            initial_request=customer_wish,
            on_log=lambda x: None,           # Terminali kirletmemesi için logları gizledik
            on_agent_status=lambda k, s: None,
            on_task_progress=lambda a, i, t, tid: None,
            on_tasks_updated=lambda t: None
        )
        
        # Sonucu kaydet
        detective_suspect = result.get("detective_conclusion", {}).get("suspect", "Bilinmiyor")
        judge_verdict = result.get("judge_verdict", {}).get("verdict", "Bilinmiyor")
        
        results.append({
            "vaka": project_name,
            "detective": detective_suspect,
            "judge": judge_verdict,
            "passed": result["pass"]
        })
        
        print(f" ✓ Bitti! | Dedektif: {detective_suspect} | Yargıç: {judge_verdict}")
        time.sleep(3) # API limitine takılmamak için bekliyoruz

    # TEST BİTİNCE TABLO YAZDIR
    print("\n" + "="*70)
    print(" 🏛️ DETEKTIF MAHKEMESI - TEST SONUÇLARI 🏛️")
    print("="*70)
    print(f"{'VAKA':<25} | {'DETEKTİF':<20} | {'YARGIÇ KARARI':<20}")
    print("-" * 70)
    
    total_guilty = 0
    for r in results:
        vaka_name = r['vaka'][:23]
        print(f"{vaka_name:<25} | {r['detective']:<20} | {r['judge']:<20}")
        if r['passed']:
            total_guilty += 1
        
    print("-" * 70)
    if len(results) > 0:
        conviction_rate = (total_guilty / len(results)) * 100
        print(f"DOĞRU SUÇLU TAYİNİ ORANI: %{conviction_rate:.1f} ({total_guilty}/{len(results)})")
    
    # Generate analytics insights
    print("\n" + "="*60)
    print(" 📊 VERI ANALİTİKS VE KARAR DESTEK 📊")
    print("="*60)
    
    analytics = DatasetAnalytics()
    report = analytics.generate_report()
    print(report)
    
    # Export metrics for further analysis
    metrics_file = analytics.export_metrics_json()
    print(f"✅ Metriks kaydedildi: {metrics_file}")
    
    # Get recommendations
    recommendations = analytics.get_recommendations()
    print("\n🎯 İYİLEŞTİRME ÖNERİLERİ:")
    for rec in recommendations:
        print(f"  {rec}")

if __name__ == "__main__":
    run_all_cases()