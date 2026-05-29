const state = {
  books: [],
  settings: null,
  question: null,
  selected: null,
  selectedImages: new Set(),
  questionLocked: false,
};

const $ = (id) => document.getElementById(id);

async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `Request failed: ${res.status}`);
  }
  return data;
}

function setFeedback(text, ok = null) {
  const el = $("feedback");
  el.textContent = text || "";
  if (ok === true) el.style.color = "#147a41";
  else if (ok === false) el.style.color = "#a62323";
  else el.style.color = "";
}

function shakeQuestionBox() {
  const box = $("questionBox");
  box.classList.remove("shake");
  void box.offsetWidth;
  box.classList.add("shake");
}

async function submitAndHandle(answer, onWrong, onCorrect) {
  if (!state.question || state.questionLocked) return;
  state.questionLocked = true;
  try {
    const data = await api("/api/answer", {
      method: "POST",
      body: JSON.stringify({ questionId: state.question.questionId, answer }),
    });

    if (data.isCorrect) {
      if (onCorrect) onCorrect();
      setFeedback("回答正确！", true);
      setTimeout(() => {
        loadSession();
      }, 420);
      return;
    }

    if (onWrong) onWrong();
    shakeQuestionBox();
    setFeedback("回答错误，请点击下一题继续", false);
  } catch (err) {
    setFeedback(err.message, false);
  } finally {
    // Wrong answer should stop auto-resubmission on the same consumed question.
    // Correct answer path will load next question shortly.
    if (state.question) {
      state.questionLocked = false;
    }
  }
}

function renderProgress(progress, dailyTarget = 20) {
  $("progressBadge").textContent = `${progress.todayReviewed} / ${dailyTarget}`;
  $("pmReviewed").textContent = String(progress.todayReviewed || 0);
  $("pmDue").textContent = String(progress.dueWords || 0);
  $("pmAcc").textContent = `${Math.round((progress.todayAccuracy || 0) * 100)}%`;
}

function toggleSettingsPanel(forceOpen = null) {
  const panel = $("settingsPanel");
  const willOpen = forceOpen === null ? panel.classList.contains("hidden") : !!forceOpen;
  panel.classList.toggle("hidden", !willOpen);
  panel.setAttribute("aria-hidden", willOpen ? "false" : "true");
}

function renderMeaningQuestion(q) {
  const box = $("questionBox");
  const opts = q.options
    .map((o) => `<button class="option-btn" data-value="${o.text}">${o.text}</button>`)
    .join("");
  box.innerHTML = `
    <p class="q-sub">Choose meaning</p>
    <p class="q-prompt">${q.prompt}</p>
    <div class="options">${opts}</div>
  `;

  state.selected = null;
  state.questionLocked = false;
  for (const btn of box.querySelectorAll(".option-btn")) {
    btn.addEventListener("click", () => {
      if (state.questionLocked) return;
      state.selected = btn.dataset.value;
      for (const b of box.querySelectorAll(".option-btn")) b.classList.remove("selected");
      btn.classList.add("selected");

      submitAndHandle(
        state.selected,
        () => {
          btn.classList.add("wrong");
        },
        () => {
          btn.classList.add("correct");
        }
      );
    });
  }
}

function renderTypingQuestion(q) {
  const box = $("questionBox");
  const isMissingVowels = q.typingMode === "missing_vowels";
  const title = isMissingVowels
    ? "Fill in missing letters (vowels)"
    : "Type the full English word/phrase";
  const placeholder = isMissingVowels ? "Type missing vowels..." : "Type full answer...";
  box.innerHTML = `
    <p class="q-sub">${title}</p>
    <p class="q-prompt">${q.prompt}</p>
    <p class="q-sub">${q.subPrompt || ""}</p>
    <input id="typingInput" type="text" placeholder="${placeholder}" />
  `;
  state.selected = null;
  state.questionLocked = false;
}

function renderImageQuestion(q) {
  const box = $("questionBox");
  const cards = q.options
    .map(
      (o) => `
      <div class="img-option" data-id="${o.id}">
        <img src="${o.imageUrl}" alt="option image" loading="lazy" />
      </div>
    `
    )
    .join("");

  box.innerHTML = `
    <p class="q-sub">Select two related images</p>
    <p class="q-prompt">${q.prompt}</p>
    <div class="img-grid">${cards}</div>
  `;

  state.selectedImages.clear();
  state.questionLocked = false;
  for (const img of box.querySelectorAll("img")) {
    img.addEventListener("error", () => {
      const seed = encodeURIComponent(`${q.prompt}-${Math.random().toString(36).slice(2, 8)}`);
      img.src = `https://picsum.photos/seed/${seed}/600/420`;
    });
  }
  for (const item of box.querySelectorAll(".img-option")) {
    item.addEventListener("click", () => {
      if (state.questionLocked) return;
      const id = item.dataset.id;
      if (state.selectedImages.has(id)) {
        state.selectedImages.delete(id);
        item.classList.remove("selected");
      } else {
        if (state.selectedImages.size >= 2) return;
        state.selectedImages.add(id);
        item.classList.add("selected");
      }

      if (state.selectedImages.size === 2) {
        const answer = Array.from(state.selectedImages.values());
        submitAndHandle(
          answer,
          () => {
            for (const card of box.querySelectorAll(".img-option.selected")) {
              card.classList.add("wrong");
            }
          },
          () => {
            for (const card of box.querySelectorAll(".img-option.selected")) {
              card.classList.add("correct");
            }
          }
        );
      }
    });
  }
}

function renderQuestion(payload) {
  state.question = payload.question;
  setFeedback("");
  if (payload.done || !state.question) {
    $("questionBox").innerHTML = `<p class="q-prompt">今天学习已完成，太棒了！</p>`;
    renderProgress(payload.progress, payload.dailyTarget || state.settings.daily_target);
    return;
  }

  renderProgress(payload.progress, payload.dailyTarget);

  const q = state.question;
  if (q.type === "meaning") renderMeaningQuestion(q);
  else if (q.type === "typing") renderTypingQuestion(q);
  else renderImageQuestion(q);
}

async function loadSession() {
  try {
    const data = await api("/api/session");
    renderQuestion(data);
  } catch (err) {
    setFeedback(err.message, false);
  }
}

function currentAnswer() {
  if (!state.question) return null;
  if (state.question.type === "meaning") return state.selected;
  if (state.question.type === "typing") return $("typingInput")?.value || "";
  return Array.from(state.selectedImages.values());
}

async function submitAnswer() {
  if (!state.question) return;
  if (state.question.type !== "typing") return;
  const answer = currentAnswer();
  if (state.question.type === "typing" && !String(answer).trim()) return setFeedback("请输入答案", false);
  await submitAndHandle(answer, null, null);
}

function fillSettingsForm() {
  const s = state.settings;
  $("dailyTarget").value = s.daily_target;
  $("modeMeaning").checked = !!s.mode_meaning;
  $("modeImage").checked = !!s.mode_image;
  $("modeTyping").checked = !!s.mode_typing;
  $("typingMode").value = s.typing_mode || "full";

  const select = $("bookSelect");
  select.innerHTML = "";
  state.books.forEach((b) => {
    const op = document.createElement("option");
    op.value = b.bookDir;
    op.textContent = b.name;
    if (b.bookDir === s.book_dir) op.selected = true;
    select.appendChild(op);
  });
}

async function saveSettings() {
  try {
    const patch = {
      book_dir: $("bookSelect").value,
      daily_target: Number($("dailyTarget").value || 20),
      mode_meaning: $("modeMeaning").checked,
      mode_image: $("modeImage").checked,
      mode_typing: $("modeTyping").checked,
      typing_mode: $("typingMode").value,
    };
    const data = await api("/api/settings", {
      method: "POST",
      body: JSON.stringify(patch),
    });
    state.settings = data.settings;
    setFeedback("设置已保存", true);
    await loadSession();
  } catch (err) {
    setFeedback(err.message, false);
  }
}

async function rebuildWordbank() {
  try {
    await api("/api/wordbank/rebuild", {
      method: "POST",
      body: JSON.stringify({ bookDir: $("bookSelect").value }),
    });
    setFeedback("词库已重建", true);
  } catch (err) {
    setFeedback(err.message, false);
  }
}

async function resetProgress() {
  if (!confirm("确认重置当前book学习进度？")) return;
  try {
    await api("/api/reset", { method: "POST" });
    setFeedback("进度已重置", true);
    await loadSession();
  } catch (err) {
    setFeedback(err.message, false);
  }
}

async function init() {
  try {
    const [books, settings] = await Promise.all([api("/api/books"), api("/api/settings")]);
    state.books = books.books || [];
    state.settings = settings.settings;
    fillSettingsForm();

    $("submitBtn").addEventListener("click", submitAnswer);
    $("nextBtn").addEventListener("click", loadSession);
    $("saveSettingsBtn").addEventListener("click", saveSettings);
    $("rebuildBtn").addEventListener("click", rebuildWordbank);
    $("resetProgressBtn").addEventListener("click", resetProgress);
    $("settingsToggleBtn").addEventListener("click", () => toggleSettingsPanel());
    $("settingsCloseBtn").addEventListener("click", () => toggleSettingsPanel(false));

    $("langBtn").addEventListener("click", async () => {
      const next = state.settings.ui_language === "zh" ? "en" : "zh";
      const data = await api("/api/settings", {
        method: "POST",
        body: JSON.stringify({ ui_language: next }),
      });
      state.settings = data.settings;
      setFeedback(next === "zh" ? "切换到中文" : "Switched to English", true);
    });

    await loadSession();
  } catch (err) {
    setFeedback(err.message, false);
  }
}

init();
