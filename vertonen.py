"""Vertont Kapitel-Textdateien mit ElevenLabs und baut die Abspielseite.
Aufruf: python vertonen.py kapitel/01_einleitung.txt
Umgebung: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (Pflicht);
          MODELL, STABILITAET, STIL, TEMPO, MAX_ZEICHEN (optional)."""
import os, sys, json, time, pathlib, urllib.request, urllib.error, html

KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE = os.environ["ELEVENLABS_VOICE_ID"]
MODELL = os.environ.get("MODELL") or "eleven_multilingual_v2"
STAB = float(os.environ.get("STABILITAET") or 0.5)
STIL = float(os.environ.get("STIL") or 0.0)
TEMPO = float(os.environ.get("TEMPO") or 1.0)
MAXZ = int(os.environ.get("MAX_ZEICHEN") or 12000)  # Schutz vor Credit-Verbrauch
BLOCK = 2500

def teile(text):
    blocks, cur = [], ""
    for p in [p.strip() for p in text.split("\n\n") if p.strip()]:
        if cur and len(cur) + len(p) + 2 > BLOCK:
            blocks.append(cur); cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur: blocks.append(cur)
    return blocks

def tts(text, davor, danach):
    body = {"text": text, "model_id": MODELL,
            "voice_settings": {"stability": STAB, "similarity_boost": 0.75,
                               "style": STIL, "use_speaker_boost": True, "speed": TEMPO}}
    if "v3" not in MODELL:
        if davor: body["previous_text"] = davor[-500:]
        if danach: body["next_text"] = danach[:500]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            print(f"HTTP {e.code}: {msg}", file=sys.stderr)
            if e.code in (429, 500, 502, 503) and versuch < 2:
                time.sleep(10 * (versuch + 1)); continue
            raise SystemExit(1)

def seite():
    mp3s = sorted(pathlib.Path("audio").glob("*.mp3"))
    zeilen = "\n".join(
        f'<section><h2>{html.escape(p.stem.replace("_"," "))}</h2>'
        f'<audio controls preload="none" src="audio/{p.name}"></audio>'
        f'<p><a href="audio/{p.name}" download>MP3 herunterladen</a></p></section>' for p in mp3s)
    pathlib.Path("index.html").write_text(f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Der eigene Ratgeber – Hörbuch (Entwurf)</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;line-height:1.4}}
section{{border-bottom:1px solid #ccc;padding:12px 0}}audio{{width:100%}}h2{{font-size:1.05rem;margin:.2rem 0}}</style></head>
<body><h1>Der eigene Ratgeber – Hörbuch</h1><p>Arbeitsstand, nur zum Probehören.</p>
{zeilen}</body></html>""", encoding="utf-8")

def main():
    pfad = pathlib.Path(sys.argv[1])
    text = pfad.read_text(encoding="utf-8").strip()
    if len(text) > MAXZ:
        print(f"Abbruch: {len(text)} Zeichen > MAX_ZEICHEN {MAXZ}", file=sys.stderr); raise SystemExit(2)
    blocks = teile(text)
    print(f"{pfad.name}: {len(text)} Zeichen, {len(blocks)} Blöcke, Modell {MODELL}, Tempo {TEMPO}")
    audio = b""
    for i, b in enumerate(blocks):
        audio += tts(b, blocks[i-1] if i else "", blocks[i+1] if i+1 < len(blocks) else "")
        print(f"  Block {i+1}/{len(blocks)} fertig")
    pathlib.Path("audio").mkdir(exist_ok=True)
    pathlib.Path("audio", pfad.stem + ".mp3").write_bytes(audio)
    seite()
    print("Fertig:", pfad.stem + ".mp3")

main()
