const state = {
  books: [],
  settings: null,
  question: null,
  selected: null,
  selectedImages: new Set(),
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

function renderProgress(progress, dailyTarget = 20) {
  $("progressBadge").textContent = `${progress.todayReviewed} / ${dailyTarget}`;
  const list = $("progressList");
  list.innerHTML = "";
  const items = [
    ["Total Words", progress.totalWords],
    ["Learned", progress.learnedWords],
    ["New", progress.newWords],
    ["Due", progress.dueWords],
    ["Today Reviewed", progress.todayReviewed],
    ["Today Correct", progress.todayCorrect],
    ["Accuracy", `${Math.round(progress.todayAccuracy * 100)}%`],
  ];
  for (const [k, v] of items) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${k}</strong><br>${v}`;
    list.appendChild(li);
  }
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
  for (const btn of box.querySelectorAll(".option-btn")) {
    btn.addEventListener("click", () => {
      state.selected = btn.dataset.value;
      for (const b of box.querySelectorAll(".option-btn")) b.classList.remove("selected");
      btn.classList.add("selected");
    });
  }
}

function renderTypingQuestion(q) {
  const box = $("questionBox");
  box.innerHTML = `
    <p class="q-sub">Type the English word/phrase</p>
    <p class="q-prompt">${q.prompt}</p>
    <input id="typingInput" type="text" placeholder="Type answer..." />
  `;
  state.selected = null;
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
  for (const img of box.querySelectorAll("img")) {
    img.addEventListener("error", () => {
      const seed = encodeURIComponent(`${q.prompt}-${Math.random().toString(36).slice(2, 8)}`);
      img.src = `https://picsum.photos/seed/${seed}/600/420`;
    });
  }
  for (const item of box.querySelectorAll(".img-option")) {
    item.addEventListener("click", () => {
      const id = item.dataset.id;
      if (state.selectedImages.has(id)) {
        state.selectedImages.delete(id);
        item.classList.remove("selected");
      } else {
        if (state.selectedImages.size >= 2) return;
        state.selectedImages.add(id);
        item.classList.add("selected");
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
  const answer = currentAnswer();
  if (state.question.type === "meaning" && !answer) return setFeedback("请选择一个答案", false);
  if (state.question.type === "image" && (!answer || answer.length !== 2)) return setFeedback("请选择两张图片", false);
  if (state.question.type === "typing" && !String(answer).trim()) return setFeedback("请输入答案", false);

  try {
    const data = await api("/api/answer", {
      method: "POST",
      body: JSON.stringify({ questionId: state.question.questionId, answer }),
    });
    setFeedback(data.isCorrect ? "回答正确！" : "再想想，下次会更好", data.isCorrect);
    await loadSession();
  } catch (err) {
    setFeedback(err.message, false);
  }
}

function fillSettingsForm() {
  const s = state.settings;
  $("dailyTarget").value = s.daily_target;
  $("modeMeaning").checked = !!s.mode_meaning;
  $("modeImage").checked = !!s.mode_image;
  $("modeTyping").checked = !!s.mode_typing;

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
