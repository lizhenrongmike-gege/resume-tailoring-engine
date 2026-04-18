(function () {
  // Shared helpers for question detection + answer auto-fill. Exposed on
  // window.JC_QUESTIONS so content.js can consume them without coupling.

  const NON_QUESTION_LABEL_REGEX =
    /^(first\s*name|last\s*name|full\s*name|preferred\s*name|email|phone|mobile|address|city|state|zip|postal|country|linkedin|github|website|portfolio|resume|cv|cover\s*letter|how\s+did\s+you\s+hear|referral|salary|current\s+company|current\s+title|date|availability)$/i;

  function visibleText(el) {
    if (!el) return "";
    return (el.innerText || el.textContent || "").trim();
  }

  function nearestLabelText(field) {
    // 1. Explicit <label for="id">
    if (field.id) {
      const lbl = document.querySelector(`label[for="${CSS.escape(field.id)}"]`);
      if (lbl) return visibleText(lbl);
    }
    // 2. Parent <label>
    const parentLabel = field.closest("label");
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true);
      // Strip the field itself from the clone so we get only the surrounding text.
      clone.querySelectorAll("input, textarea, select").forEach((n) => n.remove());
      const t = visibleText(clone);
      if (t) return t;
    }
    // 3. aria-labelledby
    const labelledBy = field.getAttribute("aria-labelledby");
    if (labelledBy) {
      const lbl = document.getElementById(labelledBy);
      if (lbl) return visibleText(lbl);
    }
    // 4. aria-label
    if (field.getAttribute("aria-label")) return field.getAttribute("aria-label").trim();
    // 5. Preceding heading or <div class*="label"> within the same form-group
    const container = field.closest("fieldset, .form-group, .field, [class*='question'], [class*='Question'], [class*='form-row']");
    if (container) {
      const heading = container.querySelector("label, legend, [class*='label'], [class*='Label'], [class*='question-title']");
      if (heading && heading !== field) {
        const t = visibleText(heading);
        if (t) return t;
      }
    }
    // 6. Previous sibling text
    let prev = field.previousElementSibling;
    for (let i = 0; i < 3 && prev; i++) {
      const t = visibleText(prev);
      if (t && t.length < 300) return t;
      prev = prev.previousElementSibling;
    }
    return "";
  }

  function extractLimits(field, labelText) {
    const maxlen = field.getAttribute("maxlength");
    const char_limit = maxlen ? parseInt(maxlen, 10) : null;

    let word_limit = null;
    // Look for "500 words", "Max 300 words", etc. in label + neighboring text
    const container = field.closest("fieldset, .form-group, .field, [class*='question'], div") || field.parentElement;
    const searchText = [labelText, container ? visibleText(container) : ""].join(" ");
    const m = searchText.match(/(?:max(?:imum)?\s+|up\s+to\s+|limit(?:ed)?\s+to\s+)?(\d{2,4})\s*words?/i);
    if (m) word_limit = parseInt(m[1], 10);
    return { char_limit, word_limit };
  }

  function looksLikeQuestion(labelText, field) {
    if (!labelText || labelText.length < 4) return false;
    if (NON_QUESTION_LABEL_REGEX.test(labelText.trim())) return false;
    if (field.type === "hidden" || field.disabled || field.readOnly) return false;
    // Require a free-text intent: textarea, OR input[type=text] with a long/instructional label
    const tag = field.tagName.toLowerCase();
    if (tag === "textarea") return true;
    if (tag === "input" && (field.type === "text" || field.type === "" || !field.type)) {
      // Short single-line inputs that look like questions (end with ?, contain phrases like "describe", "why", "what")
      return /\?\s*$/.test(labelText) || /\b(describe|why|what|how|tell\s+us|explain|share)\b/i.test(labelText);
    }
    return false;
  }

  function detect() {
    const fields = Array.from(document.querySelectorAll("textarea, input"));
    const questions = [];
    let counter = 0;
    for (const field of fields) {
      const label = nearestLabelText(field);
      if (!looksLikeQuestion(label, field)) continue;
      counter += 1;
      const { char_limit, word_limit } = extractLimits(field, label);
      const field_type = field.tagName.toLowerCase() === "textarea" ? "long_text" : "short_text";
      // Store both a stable selector and the raw text for fallback matching.
      let selector = "";
      if (field.id) selector = `#${CSS.escape(field.id)}`;
      else if (field.name) selector = `${field.tagName.toLowerCase()}[name="${CSS.escape(field.name)}"]`;
      else selector = `#__jc_q${counter}__`; // synthetic; we'll tag the element
      if (!field.id && !field.name) field.setAttribute("data-jc-question-id", `q${counter}`);
      questions.push({
        id: `q${counter}`,
        text: label,
        field_selector: selector,
        char_limit,
        word_limit,
        field_type,
      });
    }
    return questions;
  }

  function setFieldValue(field, value) {
    // Native setter + event dispatch so React/Vue/Angular pick up the change.
    const proto = field.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function flashField(field) {
    const prev = field.style.boxShadow;
    field.style.transition = "box-shadow 0.3s";
    field.style.boxShadow = "0 0 0 3px rgba(34, 197, 94, 0.7)";
    setTimeout(() => { field.style.boxShadow = prev; }, 900);
  }

  function locateField(answer) {
    // Try stored selector
    if (answer.field_selector) {
      try {
        const el = document.querySelector(answer.field_selector);
        if (el) return el;
      } catch (e) { /* invalid selector, keep trying */ }
    }
    // Synthetic selectors we set on detect()
    if (answer.id) {
      const el = document.querySelector(`[data-jc-question-id="${answer.id}"]`);
      if (el) return el;
    }
    // Fallback: match by label text
    if (answer.question_text) {
      const fields = Array.from(document.querySelectorAll("textarea, input"));
      for (const f of fields) {
        const label = nearestLabelText(f);
        if (label && label.trim() === answer.question_text.trim()) return f;
      }
    }
    return null;
  }

  function fill(answers) {
    const filled = [];
    const unmatched = [];
    for (const ans of answers) {
      const field = locateField(ans);
      if (!field) { unmatched.push(ans); continue; }
      if ((field.value || "").trim().length > 0) {
        // Never overwrite existing content — treat as unmatched for manual handling.
        unmatched.push({ ...ans, reason: "field_already_filled" });
        continue;
      }
      setFieldValue(field, ans.answer);
      flashField(field);
      filled.push(ans);
    }
    return { filled, unmatched };
  }

  window.JC_QUESTIONS = { detect, fill, nearestLabelText };
})();
