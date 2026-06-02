# DESIGN

## Goal

Build a local web app (WSL2, Python 3.12) to help a child memorize English words from the books in this repository.

The app supports:

- Book selection (currently one book).
- Daily learning target (default 20 words/day).
- Ebbinghaus-style adaptive review using SM-2.
- Three learning modes:
  - Meaning choice: see English, choose Chinese meaning.
  - Image choice: see English, choose two related images from three images.
  - Typing completion: type the English word or phrase.
- Bilingual UI (Chinese/English switch).
- Wordbank overview: side panel listing every word in the selected book with study stats (SM-2 fields, review counts) and a filter; tap a row to jump to that word in practice; download printable PDF (offline build) from the same panel.

## Architecture

### Runtime Layers

- Backend: Flask JSON API + static file serving.
- Frontend: Single-page HTML/CSS/JS (no bundler).
- Data:
  - Source vocabulary from `books/*` markdown + json.
  - Exported web wordbank JSON per book: `books/<book>/wordbank.web.json`.
  - Study state persistence in sqlite: `src/data/study.db`.

### Reused Existing Modules

Reuse existing parsing and enrichment pipeline from `src/scripts/vocab_pdf`:

- `load_book_config`
- `load_entries`
- `fill_chinese`
- `prefetch_ipa`
- `phonics_display`
- `to_ipa`
- `example_sentence`
- `clean_headword`

The web app does not require PDFs for learning, but the word list panel can trigger the same offline PDF build for download.

## Wordbank JSON Schema

Each book exports one file: `wordbank.web.json`.

```json
{
  "schemaVersion": 1,
  "book": {
    "id": "xin-jiao-ji-1-2",
    "name": "新交际一二年级",
    "outputPdf": "一年级词汇_二年级词汇_基础阅读400词汇.pdf",
    "seed": 42,
    "sourceFiles": []
  },
  "words": [
    {
      "id": "hello",
      "headword": "hello",
      "display": "hello",
      "normalized": "hello",
      "kind": "word",
      "translation": {
        "zhHans": "你好",
        "source": "book_or_cache"
      },
      "pronunciation": {
        "phonics": "h-e-ll-o",
        "ipa": "/həˈləʊ/",
        "source": "cache_or_generated"
      },
      "examples": [
        {
          "en": "Hello! I am glad to see you.",
          "zhHans": null,
          "source": "generated"
        }
      ],
      "sources": [
        {
          "label": "一年级",
          "semester": "一上",
          "unit": "U1",
          "raw": "一年级·一上·U1"
        }
      ],
      "tags": ["grade1"],
      "assets": {
        "image": null,
        "audio": null
      },
      "meta": {
        "order": 1,
        "isPhrase": false
      }
    }
  ]
}
```

## SM-2 Model

Per word state:

- `repetitions`
- `interval_days`
- `ef` (easiness factor)
- `due_date`
- `lapses`
- `correct_streak`
- `total_reviews`
- `total_correct`

Update rule:

- Convert answer to quality in [0..5].
- If quality < 3: `repetitions=0`, `interval_days=1`, `lapses += 1`.
- Else:
  - if repetitions == 0: interval = 1
  - if repetitions == 1: interval = 6
  - otherwise interval = round(interval * ef)
  - repetitions += 1
- Update EF:

$$
EF' = \max(1.3, EF + (0.1 - (5-q)(0.08 + (5-q)\cdot 0.02)))
$$

- Set `due_date = today + interval_days`.

Daily session picks due words first, then introduces new words, up to target count.

## Quiz Modes

### Meaning Choice

- Prompt: English word.
- Options: 1 correct Chinese + 2 distractors from same book.

### Image Choice

- Prompt: English word.
- Options: 3 images total.
  - 2 related images for target word.
  - 1 unrelated image from another word.
- User selects exactly two images.
- If image fetch fails, fallback to meaning mode.

### Typing Completion

- Prompt: English word clue and Chinese meaning.
- User types full English.
- Loose match:
  - lowercase compare
  - trim spaces
  - normalize punctuation and repeated spaces

## API

- `GET /api/health`
- `GET /api/books`
- `POST /api/wordbank/rebuild`
- `GET /api/settings`
- `POST /api/settings`
- `GET /api/session`
- `POST /api/answer`
- `GET /api/progress`
- `POST /api/reset`

## UI Pages

Single-page app with sections:

- Learn
- Settings
- Progress

Visual direction:

- Warm palette, playful but focused.
- Animated gradient background with card elevation.
- Strong typography with CJK-friendly families.
- Responsive layout for desktop and phone.

## Deployment / Run

- Install dependencies from `requirements.txt`.
- Launch backend:

```bash
python src/backend/app.py
```

- Open browser:

`http://127.0.0.1:5000`

## Known Limits (v1)

- Single local user profile.
- No account/login/cloud sync.
- Image source is online URL-based and may vary by network.
- Audio/TTS not included yet.
