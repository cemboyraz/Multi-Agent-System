#!/usr/bin/env python3
"""
Dataset konsolidasyon script'i
Tüm case dosyalarını (easy, medium, hard) bir dataset klasörüne toplar
"""
import os
import shutil

dataset_root = "dataset"

# Klasörleri tara
subdirs = ["easy", "medium", "hard"]

print("=" * 60)
print(" DATASET KONSOLİDASYONU BAŞLIYOR")
print("=" * 60)

total_files = 0

for subdir in subdirs:
    subdir_path = os.path.join(dataset_root, subdir)
    
    if not os.path.exists(subdir_path):
        print(f"⚠️  {subdir}/ klasörü bulunamadı")
        continue
    
    # Klasördeki tüm .txt dosyalarını bul
    txt_files = [f for f in os.listdir(subdir_path) if f.endswith('.txt')]
    
    print(f"\n[{subdir.upper()}] {len(txt_files)} case dosyası bulundu")
    
    for txt_file in txt_files:
        src = os.path.join(subdir_path, txt_file)
        dst = os.path.join(dataset_root, txt_file)
        
        # Dosyayı kopyala
        shutil.copy2(src, dst)
        print(f"  ✓ {txt_file}")
        total_files += 1

print("\n" + "=" * 60)
print(f" ✔ TAMAMLANDI: {total_files} case dosyası taşındı")
print("=" * 60)
print("\nSonraki adımlar:")
print("1. run_dataset.py çalıştır")
print("2. Eski klasörleri (easy/, medium/, hard/) silebilirsin")
