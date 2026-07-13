---
name: youtube-english-study
description: 把一支英文（或雙語）訪談／演講影片做成正體中文的雙語「英文學習」markdown 文件——逐句英中對照 + 重點單字(KK音標) + 慣用語口語解析 + 文法句型註記，文末附高頻字彙表與三步學習法。當使用者提供 YouTube（或其他）訪談/演講影片連結並要求「做一份學英文的」「參考某份 *-english-study.md 也做一份」「把這支影片做成學英文的教材」「整理成雙語逐句學習」時觸發；也適用於使用者在 learnEnglish 類資料夾中累積這類文件的情境。
---

# YouTube 訪談 → 雙語英文學習文件

把英文口語影片轉成可自學的雙語教材。成品格式固定，見 `references/format-spec.md`（撰寫任何段落前務必先讀）。

## 流程總覽

1. **抓字幕**（`scripts/get_transcript.py`）
2. **確認需求**（範圍／深度／字幕整理程度）— 用 AskUserQuestion
3. **規劃分段**（讀 `turns.txt`，依「問答主題」切段並擬中文標題）
4. **撰寫**（量少自己寫；量大用平行子代理各寫一批到獨立檔案）
5. **合併輸出**到使用者的學習資料夾，檔名 `<講者>-<主題>-english-study.md`

## 步驟 1：抓字幕

```bash
python scripts/get_transcript.py "<YouTube URL>" --out <work_dir> --zh
```

產出 `<work_dir>/turns.txt`（依說話者換手 `>>` 分輪、含 `[mm:ss]` 時間戳，**規劃與撰寫時讀這個**）與 `full.txt`。輸出摘要含總時長與英文字數，用來估算段數與工作量。

關鍵知識：
- **一定要用 `en-orig`（原生英文）**，腳本已自動優先選它。雙語訪談若誤用中文 ASR 的英文翻譯軌，來賓的英文會失真。腳本順序：`en-orig` → `en`。
- **HTTP 429 限流**是常態；腳本會自動 sleep（預設 90s）重試，通常一次就過。不要改用 `tv` player_client（會撞 DRM）。
- 若腳本抓不到英文軌，先手動 `yt-dlp --list-subs "<URL>"` 看有哪些軌別（分「automatic captions」與人工上傳的「Available subtitles」兩區）。
- 影片標題在 Windows 終端機可能顯示為亂碼（編碼問題），不影響內容；必要時寫入檔案再讀。

## 步驟 2：確認需求（AskUserQuestion）

動工前先問，因為這些大幅影響工作量與成品：
- **範圍**：整支全做 / 從某時間點起 / 只挑精華主題。
- **深度**：完整四區塊 / 精簡（只逐句對照＋單字）。
- **字幕整理程度**：輕度整理（建議）/ 完全忠實原字幕。

## 步驟 3：規劃分段

讀 `turns.txt`，以**每一組問答／主題**為一段。長的單一回答若橫跨兩個主題，可拆成兩段（在給子代理的指示中標明拆分邊界句）。為每段擬一個精準的中文標題，並記下對應的 `[mm:ss]` 時間戳範圍。開場 hook、廣告（如 "Interactive Brokers"）等略過。

## 步驟 4：撰寫

**先讀 `references/format-spec.md`**，嚴格照格式（四區塊、KK 音標、正體中文、輕度整理、`---` 分隔、不放目錄與錨點）。

- **短片／段數少**：直接自己逐段寫。
- **長片（如 40+ 分鐘、上萬字、20+ 段）**：用平行子代理分批寫，確保一致性與效率：
  1. 另寫 `00_intro.md`（導言）。
  2. 一次訊息開多個 general-purpose 子代理並行，每個負責一批連號段落。指示它：先 Read `references/format-spec.md`（skill 路徑）與 `turns.txt`，只產出指定段落到獨立檔 `part_X.md`，段間與段末加 `---`，回報完成即可。務必在每個子代理指示中**明列**它負責的段號、中文標題、對應時間戳，以及任何跨段拆分的邊界句（否則相鄰兩段會重複或遺漏）。
  3. 自己寫 `99_outro.md`（高頻字彙表 + 三步學習法）。

## 步驟 5：合併與驗證

```bash
python - <<'PY'
files=["00_intro.md","part_A.md","part_B.md","part_C.md","part_D.md","part_E.md","99_outro.md"]
out="<目標路徑>.md"
chunks=[open(f,encoding="utf-8").read().strip("\n") for f in files]
open(out,"w",encoding="utf-8").write("\n\n".join(chunks)+"\n")
PY
```

驗證：`grep -c "^## "` 段數正確且連號；抽查拆分段的接合處無重複／無遺漏；四區塊每段齊全。

## 命名與位置

輸出到使用者放這類文件的資料夾（如 `learnEnglish`），檔名沿用既有慣例：`<講者姓名>-<主題>-english-study.md`（全小寫、連字號）。
