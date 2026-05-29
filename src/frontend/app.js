const state = {
  books: [],
  settings: null,
  question: null,
  selected: null,
  selectedImages: new Set(),
  questionLocked: false,
  typingMissingCount: 0,
  typingChars: [],
  typingKeyHandler: null,
};

const $ = (id) => document.getElementById(id);

function renderInitialLoading() {
  const box = $("questionBox");
  if (!box) return;
  box.classList.add("typing-focus");

  const host = $("loadingLottie");
  if (!host) return;

  const lottie = window.lottie;
  if (!lottie || typeof lottie.loadAnimation !== "function") {
    host.innerHTML = "<p class=\"muted\">点击“下一题”开始。</p>";
    return;
  }

  lottie.loadAnimation({
    container: host,
    renderer: "svg",
    loop: true,
    autoplay: true,
    path: "/assets/Free%20Sandy%20Loading%20Animation.json",
  });
}

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
      const mark = document.createElement("span");
      mark.className = "right-mark";
      mark.textContent = "✓";
      $("questionBox").appendChild(mark);
      setTimeout(() => {
        loadSession();
      }, 1600);
      return;
    }

    if (onWrong) onWrong();
    shakeQuestionBox();
    setFeedback("回答错误", false);
    setTimeout(() => {
      loadSession();
    }, 1600);
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

function renderSourceLine(q) {
  if (!q || !q.sourceText) return "";
  return `<p class="source-line">出处 Source: ${q.sourceText}</p>`;
}

function renderIpaLine(q) {
  if (!q || !q.ipaText) return "";
  return `<p class="ipa-line">音标 IPA: ${q.ipaText}</p>`;
}

function renderMeaningQuestion(q) {
  const box = $("questionBox");
  const opts = q.options
    .map((o) => `<button class="option-btn" data-value="${o.text}">${o.text}</button>`)
    .join("");
  box.innerHTML = `
    <p class="q-sub">Choose meaning</p>
    <p class="q-prompt">${q.prompt}</p>
    ${renderIpaLine(q)}
    ${renderSourceLine(q)}
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
  let template = q.maskTemplate || "";
  if (!template) {
    const legacy = (q.subPrompt || "").trim();
    if (legacy) {
      // Legacy fallback: keep punctuation/spaces, hide alphabetic chars.
      template = legacy.replace(/[A-Za-z]/g, "_");
    }
  }
  if (!template) {
    // Absolute fallback: always render visible completion slots.
    template = "______";
  }

  state.typingMissingCount = Number(q.missingCount || 0);
  if (!state.typingMissingCount || state.typingMissingCount < 0) {
    state.typingMissingCount = Array.from(template).filter((ch) => ch === "_").length;
  }
  state.typingChars = [];
  if (state.typingKeyHandler) {
    document.removeEventListener("keydown", state.typingKeyHandler);
    state.typingKeyHandler = null;
  }

  const tokens = Array.from(template)
    .map((ch, i) => {
      if (ch === "_") {
        return `<span class="blank-slot" data-blank-idx="${i}"><span class="blank-char">&nbsp;</span></span>`;
      }
      return `<span class="fixed-char">${ch}</span>`;
    })
    .join("");

  box.innerHTML = `
    <p class="q-sub">根据中文补全单词（不显示完整英文）</p>
    <p class="q-prompt">${q.prompt}</p>
    ${renderIpaLine(q)}
    ${renderSourceLine(q)}
    <div class="completion-board" id="completionBoard">${tokens}</div>
    <p class="q-sub">键盘输入字母，Backspace 删除</p>
  `;

  box.classList.add("typing-focus");
  state.selected = null;
  state.questionLocked = false;

  const refreshTypingBoard = () => {
    const blanks = box.querySelectorAll(".blank-slot .blank-char");
    blanks.forEach((node, idx) => {
      node.textContent = state.typingChars[idx] || "";
    });
  };

  const handleKey = (e) => {
    if (!state.question || state.question.type !== "typing" || state.questionLocked) return;
    if (e.key === "Backspace") {
      if (state.typingChars.length > 0) {
        state.typingChars.pop();
        refreshTypingBoard();
      }
      e.preventDefault();
      return;
    }
    if (/^[a-zA-Z]$/.test(e.key)) {
      if (state.typingChars.length < state.typingMissingCount) {
        state.typingChars.push(e.key);
        refreshTypingBoard();
      }
      e.preventDefault();
      if (state.typingChars.length === state.typingMissingCount) {
        const answer = state.typingChars.join("");
        submitAndHandle(
          answer,
          () => {
            for (const b of box.querySelectorAll(".blank-slot")) b.classList.add("wrong");
          },
          () => {
            for (const b of box.querySelectorAll(".blank-slot")) b.classList.add("correct");
          }
        );
      }
    }
  };

  state.typingKeyHandler = handleKey;
  document.addEventListener("keydown", state.typingKeyHandler);
}

function renderImageQuestion(q) {
  const box = $("questionBox");
  box.classList.remove("typing-focus");
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
    ${renderIpaLine(q)}
    ${renderSourceLine(q)}
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
  if (state.typingKeyHandler) {
    document.removeEventListener("keydown", state.typingKeyHandler);
    state.typingKeyHandler = null;
  }
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
  if (state.question.type === "typing") return state.typingChars.join("");
  return Array.from(state.selectedImages.values());
}

async function submitAnswer() {
  if (!state.question) return;
  if (state.question.type === "typing") return;
  const answer = currentAnswer();
  if (state.question.type === "meaning" && !answer) return setFeedback("请选择一个答案", false);
  if (state.question.type === "image" && (!answer || answer.length !== 2)) return setFeedback("请选择两张图片", false);
  await submitAndHandle(answer, null, null);
}

function fillSettingsForm() {
  const s = state.settings;
  $("dailyTarget").value = s.daily_target;
  $("modeMeaning").checked = !!s.mode_meaning;
  $("modeImage").checked = !!s.mode_image;
  $("modeTyping").checked = !!s.mode_typing;
  $("typingMode").value = s.typing_mode || "missing_one_vowel";

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
    renderInitialLoading();

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
