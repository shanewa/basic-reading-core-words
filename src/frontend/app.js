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
  pendingNextTimer: null,
  continueLearning: false,
  loadInFlight: false,
  history: [],
  favorited: false,
};

const HISTORY_MAX = 50;

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
    cache: "no-store",
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

function scheduleAutoAdvance(delayMs) {
  if (state.pendingNextTimer) {
    clearTimeout(state.pendingNextTimer);
    state.pendingNextTimer = null;
  }
  state.pendingNextTimer = setTimeout(() => {
    state.pendingNextTimer = null;
    forceLoadNextSession().catch(() => {
      state.questionLocked = false;
    });
  }, delayMs);
}

async function submitAndHandle(answer, onWrong, onCorrect) {
  console.log("[wg] submitAndHandle enter", { hasQ: !!state.question, locked: state.questionLocked, answer });
  if (!state.question || state.questionLocked) {
    console.warn("[wg] submitAndHandle bail", { hasQ: !!state.question, locked: state.questionLocked });
    return;
  }
  const currentQuestionId = state.question.questionId;
  state.questionLocked = true;
  const delayMs = Math.max(100, Math.min(1000, Number(state.settings?.answer_delay_ms || 150)));
  try {
    const data = await api("/api/answer", {
      method: "POST",
      body: JSON.stringify({ questionId: state.question.questionId, answer }),
    });

    console.log("[wg] /api/answer responded", data);
    if (data.isCorrect) {
      if (onCorrect) onCorrect();
      setFeedback("回答正确！", true);
      const mark = document.createElement("span");
      mark.className = "right-mark";
      mark.textContent = "✓";
      $("questionBox").appendChild(mark);
      console.log("[wg] correct -> scheduling auto-advance", { delayMs });
      // Fire-and-forget auto-advance so it survives any interruption.
      scheduleAutoAdvance(delayMs);
      // Safety watchdog: if for any reason we're still stuck on the same
      // completed question after a generous delay, force the next load.
      setTimeout(() => {
        if (state.question && state.question.questionId === currentQuestionId) {
          forceLoadNextSession().catch(() => {
            state.questionLocked = false;
          });
        }
      }, delayMs + 1500);
      return;
    }

    if (onWrong) onWrong();
    shakeQuestionBox();
    const wrongAttempts = Number(data.wrongAttempts || 1);
    setFeedback(`回答错误，第 ${wrongAttempts} 次错误，请继续作答`, false);
    state.questionLocked = false;
  } catch (err) {
    state.questionLocked = false;
    setFeedback(err.message, false);
  }

  // Fallback: never leave the current question permanently locked.
  if (state.questionLocked && state.question && state.question.questionId === currentQuestionId) {
    state.questionLocked = false;
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

// --- Speech (TTS) ---------------------------------------------------------

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function speakerButtonHtml(text) {
  if (!text) return "";
  const safe = escapeHtml(text);
  return (
    '<button type="button" class="icon-btn speaker-btn" ' +
    `data-speak="${safe}" title="朗读 Speak" aria-label="朗读 Speak">` +
    '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">' +
    '<path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/>' +
    '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z" fill="currentColor"/>' +
    '<path d="M14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/>' +
    "</svg>" +
    "</button>"
  );
}

function pickEnglishVoice() {
  const voices = (window.speechSynthesis && window.speechSynthesis.getVoices()) || [];
  if (!voices.length) return null;
  // Prefer Google / online voices first — Microsoft Zira on Windows often goes
  // silent (start/end fire but no audio is produced). Fall back to any en-US.
  return (
    voices.find((v) => /^en/i.test(v.lang) && /google/i.test(v.name)) ||
    voices.find((v) => /^en/i.test(v.lang) && /natural|online|neural/i.test(v.name)) ||
    voices.find((v) => /en[-_]?US/i.test(v.lang) && !/zira/i.test(v.name)) ||
    voices.find((v) => /^en/i.test(v.lang) && !/zira/i.test(v.name)) ||
    voices.find((v) => /^en/i.test(v.lang)) ||
    null
  );
}

// Warm up the voice list at startup. Some browsers (Chrome) load voices async.
if ("speechSynthesis" in window) {
  try {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.addEventListener &&
      window.speechSynthesis.addEventListener("voiceschanged", () => {
        const vs = window.speechSynthesis.getVoices();
        console.log(`[wg] voices loaded: ${vs.length}`, vs.slice(0, 5).map((v) => `${v.name} (${v.lang})`));
      });
  } catch (e) {
    /* ignore */
  }
}

function actuallySpeak(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 0.85;
  u.pitch = 1.0;
  u.volume = 1.0;
  const preferred = pickEnglishVoice();
  if (preferred) {
    u.voice = preferred;
    u.lang = preferred.lang || "en-US";
  }
  const t0 = performance.now();
  u.onstart = () =>
    console.log(`[wg] speak start: "${text}" voice=${u.voice && u.voice.name}`);
  u.onerror = (e) => console.warn("[wg] speak error", e.error || e);
  u.onend = () => {
    const dt = (performance.now() - t0).toFixed(0);
    console.log(`[wg] speak end (${dt}ms)`);
  };
  window.speechSynthesis.speak(u);
}

function speakText(text) {
  if (!text) return;
  if (!("speechSynthesis" in window)) {
    setFeedback("浏览器不支持朗读 Speech not supported", false);
    return;
  }
  console.log(`[wg] speakText invoked: "${text}"`);
  try {
    window.speechSynthesis.cancel();
  } catch (e) {
    /* ignore */
  }
  // Chrome glitch: speak() right after cancel() sometimes silently no-ops.
  // A tiny delay avoids this reliably.
  setTimeout(() => {
    try {
      // If voices still empty, getVoices once more to nudge async load, then speak.
      const voices = window.speechSynthesis.getVoices();
      if (!voices.length) {
        console.log("[wg] voices not ready yet, speaking with default voice");
      }
      actuallySpeak(text);
    } catch (err) {
      console.warn("[wg] speak failed", err);
    }
  }, 60);
}

// Single delegated handler for any .speaker-btn inside the question box.
document.addEventListener("click", (e) => {
  const btn = e.target.closest && e.target.closest(".speaker-btn");
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  speakText(btn.getAttribute("data-speak"));
});

function renderMeaningQuestion(q) {
  const box = $("questionBox");
  const opts = q.options
    .map((o) => `<button class="option-btn" data-value="${o.text}">${o.text}</button>`)
    .join("");
  box.innerHTML = `
    <p class="q-sub">Choose meaning</p>
    <p class="q-prompt with-speaker">${q.prompt}${speakerButtonHtml(q.headword || q.prompt)}</p>
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
          for (const b of box.querySelectorAll(".option-btn")) b.classList.remove("wrong", "correct");
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
    <p class="q-prompt with-speaker">${q.prompt}${speakerButtonHtml(q.headword)}</p>
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
            state.typingChars = [];
            refreshTypingBoard();
            setTimeout(() => {
              for (const b of box.querySelectorAll(".blank-slot")) b.classList.remove("wrong");
            }, 260);
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
    <p class="q-prompt with-speaker">${q.prompt}${speakerButtonHtml(q.headword || q.prompt)}</p>
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
            setTimeout(() => {
              state.selectedImages.clear();
              for (const card of box.querySelectorAll(".img-option")) {
                card.classList.remove("selected", "wrong", "correct");
              }
            }, 280);
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

function updateFavoriteButton() {
  const btn = $("favoriteBtn");
  if (!btn) return;
  const hasWord = !!(state.question && state.question.wordId);
  btn.disabled = !hasWord;
  btn.classList.toggle("is-favorited", !!state.favorited);
  btn.setAttribute(
    "aria-pressed",
    state.favorited ? "true" : "false"
  );
  btn.title = state.favorited ? "取消收藏 Unfavorite" : "收藏 Favorite";
}

function toggleFavoritesPanel(forceOpen = null) {
  const panel = $("favoritesPanel");
  if (!panel) return;
  const willOpen = forceOpen === null ? panel.classList.contains("hidden") : !!forceOpen;
  panel.classList.toggle("hidden", !willOpen);
  panel.setAttribute("aria-hidden", willOpen ? "false" : "true");
  if (willOpen) {
    loadAndRenderFavorites();
  }
}

async function loadAndRenderFavorites() {
  const listEl = $("favoritesList");
  const emptyEl = $("favoritesEmpty");
  if (!listEl) return;
  listEl.innerHTML = '<li class="muted">加载中... Loading…</li>';
  emptyEl.classList.add("hidden");
  try {
    const data = await api("/api/favorites");
    const items = data.items || [];
    renderFavoritesList(items);
  } catch (err) {
    listEl.innerHTML = `<li class="muted">加载失败：${err.message}</li>`;
  }
}

function renderFavoritesList(items) {
  const listEl = $("favoritesList");
  const emptyEl = $("favoritesEmpty");
  if (!listEl) return;
  listEl.innerHTML = "";
  if (!items.length) {
    emptyEl.classList.remove("hidden");
    return;
  }
  emptyEl.classList.add("hidden");
  for (const item of items) {
    const li = document.createElement("li");

    const info = document.createElement("div");
    info.className = "fav-info";
    info.title = "去做这个词的题 Go to this word";
    const head = document.createElement("div");
    head.className = "fav-head" + (item.missing ? " fav-missing" : "");
    head.textContent = item.headword + (item.missing ? "  (已不在当前书) (no longer in book)" : "");
    const zh = document.createElement("div");
    zh.className = "fav-zh";
    zh.textContent = item.zhHans || "";
    info.appendChild(head);
    if (item.zhHans) info.appendChild(zh);
    info.addEventListener("click", async () => {
      if (item.missing) return;
      toggleFavoritesPanel(false);
      // Reset history-current so prev still works naturally.
      await loadSession({ wordId: item.wordId });
    });

    const removeBtn = document.createElement("button");
    removeBtn.className = "icon-btn favorite-btn is-favorited";
    removeBtn.title = "取消收藏 Remove";
    removeBtn.setAttribute("aria-label", "取消收藏 Remove");
    removeBtn.innerHTML =
      '<svg class="star-icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">' +
      '<path class="star-path" d="M12 2.5l2.95 6.36 7.05.74-5.3 4.86 1.57 7.04L12 17.9l-6.27 3.6 1.57-7.04L2 9.6l7.05-.74L12 2.5z" />' +
      "</svg>";
    removeBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await api("/api/favorites/toggle", {
          method: "POST",
          body: JSON.stringify({ wordId: item.wordId }),
        });
        // If the removed word is the one currently displayed, sync the star.
        if (state.question && state.question.wordId === item.wordId) {
          state.favorited = false;
          updateFavoriteButton();
        }
        await loadAndRenderFavorites();
      } catch (err) {
        setFeedback(err.message, false);
      }
    });

    li.appendChild(info);
    li.appendChild(removeBtn);
    listEl.appendChild(li);
  }
}

async function toggleFavorite() {
  if (!state.question || !state.question.wordId) return;
  const wordId = state.question.wordId;
  // Optimistic toggle.
  const prev = state.favorited;
  state.favorited = !prev;
  updateFavoriteButton();
  try {
    const data = await api("/api/favorites/toggle", {
      method: "POST",
      body: JSON.stringify({ wordId }),
    });
    state.favorited = !!data.favorited;
  } catch (err) {
    state.favorited = prev;
    setFeedback(err.message, false);
  }
  updateFavoriteButton();
}

function updatePrevButton() {
  const btn = $("prevBtn");
  if (!btn) return;
  // Need at least 2 entries: the current one (last) + one previous to jump to.
  btn.disabled = state.history.length < 2;
}

function pushHistory(wordId) {
  if (!wordId) return;
  // Avoid duplicating the same word back-to-back.
  if (state.history[state.history.length - 1] === wordId) return;
  state.history.push(wordId);
  if (state.history.length > HISTORY_MAX) {
    state.history.splice(0, state.history.length - HISTORY_MAX);
  }
  updatePrevButton();
}

function renderQuestion(payload) {
  state.question = payload.question;
  state.favorited = !!payload.favorited;
  if (state.typingKeyHandler) {
    document.removeEventListener("keydown", state.typingKeyHandler);
    state.typingKeyHandler = null;
  }
  setFeedback("");
  if (payload.done || !state.question) {
    const canContinue = !!payload.canContinue;
    $("questionBox").innerHTML = `
      <p class="q-prompt">今天学习已完成，太棒了！</p>
      ${canContinue ? '<button id="continueLearningBtn" class="primary-btn">继续学习 Continue</button>' : ""}
    `;
    if (canContinue) {
      const btn = $("continueLearningBtn");
      if (btn) {
        btn.addEventListener("click", async () => {
          state.continueLearning = true;
          await loadSession();
        });
      }
    }
    renderProgress(payload.progress, payload.dailyTarget || state.settings.daily_target);
    updatePrevButton();
    updateFavoriteButton();
    return;
  }

  renderProgress(payload.progress, payload.dailyTarget);
  pushHistory(state.question.wordId);
  updateFavoriteButton();

  const q = state.question;
  if (q.type === "meaning") renderMeaningQuestion(q);
  else if (q.type === "typing") renderTypingQuestion(q);
  else renderImageQuestion(q);
}

async function loadSession(opts = {}) {
  if (state.loadInFlight) {
    console.warn("[wg] loadSession already in flight; ignoring duplicate call");
    return;
  }
  state.loadInFlight = true;
  const t0 = performance.now();
  try {
    if (state.pendingNextTimer) {
      clearTimeout(state.pendingNextTimer);
      state.pendingNextTimer = null;
    }
    const params = new URLSearchParams();
    if (opts.wordId) {
      params.set("wordId", opts.wordId);
    } else if (state.continueLearning) {
      params.set("continue", "1");
    }
    const qs = params.toString();
    const url = qs ? `/api/session?${qs}` : "/api/session";
    const data = await api(url);
    console.log(`[wg] /api/session took ${(performance.now() - t0).toFixed(0)}ms`);
    renderQuestion(data);
  } catch (err) {
    state.questionLocked = false;
    setFeedback(err.message, false);
    console.error("[wg] loadSession failed", err);
  } finally {
    state.loadInFlight = false;
  }
}

async function loadPreviousSession() {
  console.log("[wg] loadPreviousSession called", { historyLen: state.history.length });
  if (state.history.length < 2) {
    setFeedback("没有更早的题目了 No earlier question", false);
    return;
  }
  // Pop current and previous; renderQuestion will re-push the previous one.
  state.history.pop(); // current
  const prevWordId = state.history.pop();
  updatePrevButton();
  if (state.pendingNextTimer) {
    clearTimeout(state.pendingNextTimer);
    state.pendingNextTimer = null;
  }
  if (state.typingKeyHandler) {
    document.removeEventListener("keydown", state.typingKeyHandler);
    state.typingKeyHandler = null;
  }
  state.questionLocked = false;
  try {
    await loadSession({ wordId: prevWordId });
  } finally {
    state.questionLocked = false;
  }
}

async function forceLoadNextSession() {
  console.log("[wg] forceLoadNextSession called", { locked: state.questionLocked, hasQ: !!state.question });
  if (state.pendingNextTimer) {
    clearTimeout(state.pendingNextTimer);
    state.pendingNextTimer = null;
  }
  if (state.typingKeyHandler) {
    document.removeEventListener("keydown", state.typingKeyHandler);
    state.typingKeyHandler = null;
  }
  // If on completed screen, next should continue learning immediately.
  if (!state.question) {
    state.continueLearning = true;
  }
  state.questionLocked = false;
  try {
    await loadSession();
  } finally {
    // Belt-and-suspenders: ensure we never leave the UI locked after a
    // navigation attempt, even if rendering throws unexpectedly.
    state.questionLocked = false;
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
  $("answerDelayMs").value = s.answer_delay_ms || 150;
  $("modeMeaning").checked = !!s.mode_meaning;
  $("modeImage").checked = !!s.mode_image;
  $("modeTyping").checked = !!s.mode_typing;

  // Compatibility mapping for old stored values.
  const modeMap = {
    full: "all_missing",
    missing_vowels: "missing_multi_vowels",
    missing_one_vowel: "missing_one_vowel",
    missing_multi_vowels: "missing_multi_vowels",
    all_missing: "all_missing",
  };
  const normalizedTypingMode = modeMap[s.typing_mode] || "missing_multi_vowels";
  $("typingMode").value = normalizedTypingMode;

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
    state.continueLearning = false;
    state.history = [];
    updatePrevButton();
    const patch = {
      book_dir: $("bookSelect").value,
      daily_target: Number($("dailyTarget").value || 20),
      answer_delay_ms: Number($("answerDelayMs").value || 150),
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
    state.continueLearning = false;
    state.history = [];
    updatePrevButton();
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
    $("nextBtn").addEventListener("click", forceLoadNextSession);
    $("prevBtn").addEventListener("click", loadPreviousSession);
    $("favoriteBtn").addEventListener("click", toggleFavorite);
    $("favoritesToggleBtn").addEventListener("click", () => toggleFavoritesPanel());
    $("favoritesCloseBtn").addEventListener("click", () => toggleFavoritesPanel(false));
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
