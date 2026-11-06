#!/usr/bin/env python3
"""
GPU Performance Benchmark for CosyVoice 3 (Fun-CosyVoice3-0.5B)
Cross-platform: Windows and Linux (Ubuntu + RTX 3070 GPU Unlock)

Synthesizes 5 standardized Russian paragraphs (~65-84 tokens each)
and measures RTF, throughput, and model load time.
Automatically compares against Windows baseline if available.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# --- 5 standardized test paragraphs from Chapter 3 ---
BENCH_TEXTS = [
    "Глава третья. К середине ноября Гарри уже начал жалеть, что не может сыграть свой первый матч по квиддичу, пока об этом ещё никто не узнал. На лестнице второкурсник из Пуффендуя пожелал ему удачи.",
    "Гарри поблагодарил его, а затем следующие два пролёта гадал, откуда незнакомцу известно, на какой позиции он играет. К обеду всё стало ясно: оказывается, об этом знали все.",
    "Незнакомая ему когтевранка спросила, правда ли, что он поймал Напоминалку, нырнув с высоты пятидесяти футов. К обеду высота выросла до семидесяти.",
    "За ужином Гарри услышал, как двое гриффиндорцев уверяют, будто во время того трюка он стоял на метле. — Я бы не советовала тебе пробовать, — сказала Гермиона. Гарри разломил хлеб пополам. — Да я и не собирался.",
    "— А вид у тебя был заинтересованный. — Мне просто любопытно, как они себе это представляют. — Людям больше нравятся впечатляющие истории, а не правдивые. Через зал со стола Слизерина взлетела маленькая бумажная птичка.",
]


def find_ai_dubbing_root(custom_root=None):
    candidates = []
    if custom_root:
        candidates.append(Path(custom_root))
    if os.environ.get("AI_DUBBING_ROOT"):
        candidates.append(Path(os.environ["AI_DUBBING_ROOT"]))

    cwd = Path.cwd()
    candidates.extend([
        cwd,
        cwd / "AI-Dubbing",
        Path.home() / "AI-Dubbing",
        Path("/mnt/ai/AI-Dubbing"),
        Path("/mnt/ai"),
        Path(r"E:\AI-Dubbing"),
    ])

    for p in candidates:
        if (p / "CosyVoice").is_dir() and (p / "voices").is_dir():
            return p.resolve()
        # Alternatively if we are already inside CosyVoice
        if (p / "pretrained_models").is_dir() and (p / "cosyvoice").is_dir():
            return p.parent.resolve()

    # Fallback to current working directory or first candidate
    return candidates[0].resolve() if candidates else cwd.resolve()


def parse_args():
    parser = argparse.ArgumentParser(description="CosyVoice 3 GPU Benchmark (Windows & Linux)")
    parser.add_argument("--root", type=str, default=None, help="Root path to AI-Dubbing repository")
    parser.add_argument("--model-dir", type=str, default=None, help="Path to Fun-CosyVoice3-0.5B directory")
    parser.add_argument("--voice", type=str, default=None, help="Path to voice reference wav file")
    parser.add_argument("--ref-txt", type=str, default=None, help="Path to voice reference transcript txt")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory for generated wavs and report")
    parser.add_argument("--baseline", type=str, default=None, help="Path to baseline JSON report for comparison")
    return parser.parse_args()


def main():
    args = parse_args()
    platform_name = "Linux" if sys.platform.startswith("linux") else "Windows"

    root_dir = find_ai_dubbing_root(args.root)
    cosy_dir = root_dir / "CosyVoice"
    matcha_dir = cosy_dir / "third_party" / "Matcha-TTS"

    # Set up sys.path
    for p in [str(root_dir), str(cosy_dir), str(matcha_dir)]:
        if p not in sys.path and os.path.exists(p):
            sys.path.insert(0, p)

    # Import torch and cosyvoice after path setup
    try:
        import torch
        import torchaudio
        from cosyvoice.cli.cosyvoice import AutoModel
    except ImportError as e:
        print(f"Error importing CosyVoice or PyTorch dependencies: {e}")
        print("Please activate your virtual environment before running:")
        print("  Windows: E:\\AI-Dubbing\\cosyvoice_env\\Scripts\\activate")
        print("  Linux:   source ~/cosyvoice-env/bin/activate")
        sys.exit(1)

    model_dir = Path(args.model_dir) if args.model_dir else (cosy_dir / "pretrained_models" / "Fun-CosyVoice3-0.5B")
    voice_file = Path(args.voice) if args.voice else (root_dir / "voices" / "VID_20261101_122350_289.wav")
    ref_txt = Path(args.ref_txt) if args.ref_txt else (root_dir / "voices" / "VID_20261101_122350_289.reference.txt")

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_name = "bench_linux" if platform_name == "Linux" else "bench_win"
        out_dir = root_dir / "output" / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== {platform_name} GPU Benchmark: CosyVoice 3 (Fun-CosyVoice3-0.5B) ===\n")
    print(f"Root dir:   {root_dir}")
    print(f"Model dir:  {model_dir}")
    print(f"Voice file: {voice_file}")
    print(f"Output dir: {out_dir}\n")

    if not voice_file.exists():
        print(f"WARNING: Voice reference file not found at {voice_file}")
    if not ref_txt.exists():
        print(f"WARNING: Voice transcript file not found at {ref_txt}")

    # GPU info
    gpu_name = "CPU"
    vram_total = 0.0
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        gpu_name = props.name
        vram_total = props.total_memory / (1024**3)
        print(f"GPU: {gpu_name}  VRAM: {vram_total:.1f} GB")
        print(f"CUDA version: {torch.version.cuda}")
    else:
        print("GPU: not available (CPU mode)")
    print()

    # Load model
    print("Loading CosyVoice model...")
    t_load = time.perf_counter()
    cosyvoice = AutoModel(model_dir=str(model_dir))
    sr = cosyvoice.sample_rate
    load_time = time.perf_counter() - t_load
    print(f"Model load time: {load_time:.2f}s  |  Sample rate: {sr} Hz\n")

    # Read reference transcript
    with open(ref_txt, encoding="utf-8") as f:
        ref_transcript = f.read().strip()
    prompt_text = f"You are a helpful assistant.<|endofprompt|>{ref_transcript}"

    results = []
    total_audio_s = 0.0
    total_synth_s = 0.0

    print("Running synthesis benchmark (5 segments)...")
    for i, text in enumerate(BENCH_TEXTS, 1):
        t0 = time.perf_counter()
        outputs = list(cosyvoice.inference_zero_shot(
            tts_text=text,
            prompt_text=prompt_text,
            prompt_wav=str(voice_file),
            stream=False,
            speed=1.0,
            text_frontend=False,
        ))
        synth_time = time.perf_counter() - t0
        audio = torch.concat([o["tts_speech"] for o in outputs], dim=1)
        audio_dur = audio.shape[1] / sr
        rtf = synth_time / audio_dur

        out_wav = out_dir / f"bench_{i:02d}.wav"
        torchaudio.save(str(out_wav), audio, sr)

        total_audio_s += audio_dur
        total_synth_s += synth_time

        print(f"[{i}/{len(BENCH_TEXTS)}] "
              f"chars={len(text):3d}  "
              f"audio={audio_dur:5.2f}s  "
              f"synth={synth_time:5.2f}s  "
              f"RTF={rtf:.3f}  "
              f"speed={audio_dur/synth_time:.2f}x")

        results.append({
            "idx": i,
            "chars": len(text),
            "audio_s": round(audio_dur, 3),
            "synth_s": round(synth_time, 3),
            "rtf": round(rtf, 4),
            "speedup": round(audio_dur / synth_time, 3),
        })

    avg_rtf = total_synth_s / total_audio_s
    throughput = total_audio_s / total_synth_s

    print("\n=== SUMMARY ===")
    print(f"Platform:          {platform_name}")
    print(f"GPU:               {gpu_name} ({vram_total:.1f} GB)")
    print(f"Model load:        {load_time:.2f}s")
    print(f"Total audio:       {total_audio_s:.2f}s  ({total_audio_s/60:.2f} min)")
    print(f"Total synth time:  {total_synth_s:.2f}s  ({total_synth_s/60:.2f} min)")
    print(f"Average RTF:       {avg_rtf:.4f}  (1.0 = real-time)")
    print(f"Throughput:        {throughput:.3f}x  ({throughput*60:.1f} min audio per min compute)")
    print()

    # Save JSON report
    report_filename = f"bench_report_{platform_name.lower()}.json"
    report_path = out_dir / report_filename

    report = {
        "platform": platform_name,
        "gpu": gpu_name,
        "vram_gb": round(vram_total, 1),
        "model_load_s": round(load_time, 2),
        "total_audio_s": round(total_audio_s, 3),
        "total_synth_s": round(total_synth_s, 3),
        "avg_rtf": round(avg_rtf, 4),
        "throughput_x": round(throughput, 3),
        "segments": results,
    }

    # Baseline comparison (e.g. against Windows)
    baseline_file = None
    if args.baseline:
        baseline_file = Path(args.baseline)
    else:
        # Check current dir, script dir, or output dir
        script_dir = Path(__file__).resolve().parent
        for candidate in [
            script_dir / "bench_report_windows.json",
            Path.cwd() / "bench_report_windows.json",
            root_dir / "output" / "bench_win" / "bench_report_windows.json",
        ]:
            if candidate.is_file():
                baseline_file = candidate
                break

    if baseline_file and baseline_file.is_file():
        try:
            with open(baseline_file, encoding="utf-8") as f:
                base = json.load(f)

            base_rtf = base.get("avg_rtf", 1.0)
            base_tp = base.get("throughput_x", 1.0)
            base_load = base.get("model_load_s", 0.0)
            base_synth = base.get("total_synth_s", 0.0)

            rtf_diff_pct = ((avg_rtf - base_rtf) / base_rtf) * 100.0
            tp_diff_pct = ((throughput - base_tp) / base_tp) * 100.0
            load_diff_pct = ((load_time - base_load) / base_load) * 100.0 if base_load else 0.0
            synth_diff_pct = ((total_synth_s - base_synth) / base_synth) * 100.0 if base_synth else 0.0

            print("==========================================================================")
            print(f"📊 COMPARISON: Baseline ({base.get('platform', 'Windows')}) vs Current ({platform_name})")
            print("==========================================================================")
            print(f"{'Metric':<20} | {'Baseline':<18} | {'Current':<18} | {'Delta':<15}")
            print("-" * 74)
            print(f"{'Model Load':<20} | {base_load:>16.2f}s | {load_time:>16.2f}s | {load_diff_pct:>+13.1f}%")
            print(f"{'Total Synth Time':<20} | {base_synth:>16.2f}s | {total_synth_s:>16.2f}s | {synth_diff_pct:>+13.1f}%")
            print(f"{'Average RTF':<20} | {base_rtf:>18.4f} | {avg_rtf:>18.4f} | {rtf_diff_pct:>+13.1f}%")
            print(f"{'Throughput':<20} | {base_tp:>17.3f}x | {throughput:>17.3f}x | {tp_diff_pct:>+13.1f}%")
            print("==========================================================================")

            if rtf_diff_pct < 0:
                print(f"🚀 Speedup achieved: {-rtf_diff_pct:.1f}% faster generation on {platform_name}!")
            print()

            report["comparison_against_baseline"] = {
                "baseline_file": str(baseline_file),
                "baseline_platform": base.get("platform", "Windows"),
                "rtf_delta_pct": round(rtf_diff_pct, 2),
                "throughput_delta_pct": round(tp_diff_pct, 2),
                "synth_time_delta_pct": round(synth_diff_pct, 2),
            }
        except Exception as ex:
            print(f"Note: Could not compare against baseline: {ex}")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved: {report_path}")

    # Also save a copy in script dir if running in repo
    local_copy = Path(__file__).resolve().parent / report_filename
    if local_copy != report_path:
        with open(local_copy, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Local copy saved: {local_copy}")


if __name__ == "__main__":
    main()
