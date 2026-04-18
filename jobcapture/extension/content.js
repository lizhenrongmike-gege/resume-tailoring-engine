(function () {
  if (document.getElementById("jc-float")) return; // already injected

  const API = JOBCAPTURE_CONFIG.API_BASE_URL;
  const isLinkedIn = window.location.hostname.includes("linkedin.com");

  // ── Job extraction ──────────────────────────────────────────

  function firstMatch(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) return el;
    }
    return null;
  }

  function extractLinkedIn() {
    const data = {
      company: null, company_url: null, title: null, description: null,
      application_url: window.location.href, location: null, source_site: "linkedin",
    };

    // Job title — covers /jobs/search/, /jobs/view/, and /jobs/collections/
    const titleEl = firstMatch([
      // /jobs/search/ (detail pane)
      ".job-details-jobs-unified-top-card__job-title h1",
      ".job-details-jobs-unified-top-card__job-title a",
      ".job-details-jobs-unified-top-card__job-title",
      // /jobs/view/ (full page - logged in)
      ".jobs-unified-top-card__job-title h1",
      ".jobs-unified-top-card__job-title",
      ".job-details-jobs-unified-top-card__job-title h1 a",
      // /jobs/view/ (full page - public)
      ".top-card-layout__title",
      ".topcard__title",
      // Generic class patterns
      "h1[class*='job-title']",
      "h1[class*='topcard']",
      "h1.t-24",
      ".t-24.t-bold",
      // h2 fallback (some layouts use h2 for job title)
      "h2[class*='job-title']",
      "h2.t-24",
      "h2.t-bold",
      // Last resort: h1, then h2
      "h1",
      "h2",
    ]);
    if (titleEl) data.title = titleEl.textContent.trim();

    // If title looks like it grabbed the wrong thing (too long or is company name), try og:title
    if (!data.title || data.title.length > 120) {
      const ogTitle = document.querySelector('meta[property="og:title"]');
      if (ogTitle && ogTitle.content) {
        // LinkedIn og:title format is usually "Job Title - Company | LinkedIn"
        const parts = ogTitle.content.split(/\s*[-|]\s*/);
        if (parts.length > 0) data.title = parts[0].trim();
      }
    }
    // Fallback: extract from document title "Job Title | Company | LinkedIn"
    if (!data.title) {
      const parts = document.title.split(/\s*[-|]\s*/);
      if (parts.length >= 2) data.title = parts[0].trim();
    }

    // Company name
    const compEl = firstMatch([
      // /jobs/search/
      ".job-details-jobs-unified-top-card__company-name a",
      ".job-details-jobs-unified-top-card__company-name",
      // /jobs/view/
      ".top-card-layout__card a.topcard__org-name-link",
      ".topcard__org-name-link",
      "a[data-tracking-control-name='public_jobs_topcard-org-name']",
      ".top-card-layout__second-subline a",
      // Generic
      ".jobs-unified-top-card__company-name a",
      ".jobs-unified-top-card__company-name",
      ".job-details-jobs-unified-top-card__primary-description-container a",
      // Broad fallback
      "a[href*='/company/']",
    ]);
    if (compEl && compEl.textContent.trim().length < 100) {
      data.company = compEl.textContent.trim();
      // Grab the company LinkedIn page URL from the link
      const compLink = compEl.tagName === "A" ? compEl : compEl.querySelector("a");
      if (compLink && compLink.href && compLink.href.includes("/company/")) {
        data.company_url = compLink.href.split("?")[0]; // strip tracking params
      }
    }

    // Location
    const locEl = firstMatch([
      // /jobs/search/
      ".job-details-jobs-unified-top-card__bullet",
      ".jobs-unified-top-card__bullet",
      // /jobs/view/
      ".top-card-layout__bullet",
      ".topcard__flavor--bullet",
      "span.topcard__flavor:not(.topcard__flavor--bullet)",
      // Generic
      "[class*='top-card'] [class*='bullet']",
      "[class*='top-card'] [class*='workplace']",
    ]);
    if (locEl && locEl.textContent.trim().length < 80) {
      data.location = locEl.textContent.trim();
    }
    // Fallback: parse location from primary description or subtitle area
    if (!data.location) {
      const containers = [
        ".job-details-jobs-unified-top-card__primary-description-container",
        ".top-card-layout__second-subline",
        ".topcard__content-left",
      ];
      for (const sel of containers) {
        const dc = document.querySelector(sel);
        if (dc) {
          const m = dc.textContent.match(/([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}(?:\s*\([^)]+\))?)/)
            || dc.textContent.match(/(United States|Remote|Worldwide)/i);
          if (m) { data.location = m[1].trim(); break; }
        }
      }
    }

    // Apply link — build the canonical LinkedIn job view URL.
    // LinkedIn is a SPA: old job data (JSON, embedded URLs) stays in the
    // page HTML when you click through search results, making it impossible
    // to reliably extract external apply URLs from the DOM or raw HTML.
    // Instead, we build a clean permalink from the current job ID.
    // When the job has an external apply (Greenhouse, Lever, etc.), the user
    // clicks "Apply" on this LinkedIn page and gets redirected there.
    const jobIdMatch = window.location.href.match(/currentJobId=(\d+)/)
      || window.location.href.match(/\/jobs\/view\/(\d+)/);
    if (jobIdMatch) {
      data.application_url = `https://www.linkedin.com/jobs/view/${jobIdMatch[1]}/`;
    }

    // Job description
    const descEl = firstMatch([
      "#job-details",
      ".jobs-description__content",
      ".jobs-description-content__text",
      ".jobs-box__html-content",
      // /jobs/view/ (logged in)
      ".jobs-description",
      ".jobs-description__container",
      // /jobs/view/ (public)
      ".description__text",
      ".show-more-less-html__markup",
      ".top-card-layout .description",
      // Generic
      "[class*='jobs-description']",
      "[class*='description__text']",
      "[class*='job-description']",
    ]);
    if (descEl && descEl.innerText.trim().length > 50) {
      data.description = descEl.innerText.trim();
    }
    // Fallback: find "About the job" heading and grab everything after it
    if (!data.description) {
      const headings = document.querySelectorAll("h2, h3, .t-20, .t-bold");
      for (const h of headings) {
        if (h.textContent.trim().toLowerCase().includes("about the job")) {
          // Grab the parent section or next siblings
          const section = h.closest("section") || h.closest("div[class*='description']") || h.parentElement;
          if (section && section.innerText.trim().length > 100) {
            data.description = section.innerText.trim();
            break;
          }
        }
      }
    }
    // Last resort: grab article or main content
    if (!data.description) {
      const main = document.querySelector("article") || document.querySelector("main");
      if (main && main.innerText.trim().length > 200) {
        data.description = main.innerText.trim();
      }
    }

    return data;
  }

  function extractGeneric() {
    const data = {
      company: null, company_url: null, title: null, description: null,
      application_url: window.location.href, location: null,
      source_site: window.location.hostname.replace("www.", ""),
    };

    // ── 1. Try JSON-LD structured data FIRST (most reliable) ──
    // ATS platforms (Greenhouse, Lever, Workday, Ashby, iCIMS, SmartRecruiters,
    // Jobvite, BambooHR, etc.) emit standardized JobPosting schema
    let jobPosting = null;
    for (const sc of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        let ld = JSON.parse(sc.textContent);
        // Handle @graph arrays (some sites wrap in @graph)
        if (ld["@graph"]) ld = ld["@graph"].find(item => item["@type"] === "JobPosting") || ld;
        // Handle arrays
        if (Array.isArray(ld)) ld = ld.find(item => item["@type"] === "JobPosting") || ld[0];
        if (ld["@type"] === "JobPosting") { jobPosting = ld; break; }
      } catch (e) {}
    }

    if (jobPosting) {
      data.title = jobPosting.title || null;
      // Company from hiringOrganization
      const org = jobPosting.hiringOrganization;
      if (org) {
        data.company = typeof org === "string" ? org : (org.name || null);
        // Extract actual company website URL from JSON-LD
        if (typeof org === "object") {
          data.company_url = org.sameAs || org.url || null;
        }
      }
      // Location from jobLocation
      const loc = jobPosting.jobLocation;
      if (loc) {
        if (Array.isArray(loc)) {
          // Multiple locations — take the first
          const first = loc[0];
          const addr = first.address || first;
          data.location = [addr.addressLocality, addr.addressRegion, addr.addressCountry]
            .filter(v => v && typeof v === "string").join(", ");
        } else {
          const addr = loc.address || loc;
          if (typeof addr === "string") data.location = addr;
          else data.location = [addr.addressLocality, addr.addressRegion]
            .filter(v => v && typeof v === "string").join(", ");
        }
      }
      if (jobPosting.jobLocationType) {
        data.location = (data.location || "") + (data.location ? " " : "") + `(${jobPosting.jobLocationType})`;
      }
      // Description from JSON-LD (may be HTML)
      if (jobPosting.description) {
        const tmp = document.createElement("div");
        tmp.innerHTML = jobPosting.description;
        data.description = tmp.innerText.trim();
      }
      // Apply URL — on ATS sites (Greenhouse, Lever, etc.) the user is
      // already on the application page, so always keep window.location.href.
      // JSON-LD url fields on these sites can point to stale/wrong jobs.
    }

    // ── 2. Fill gaps with meta tags ──
    if (!data.title) {
      const ogTitle = document.querySelector('meta[property="og:title"]');
      if (ogTitle && ogTitle.content) {
        // Strip common suffixes like "| Company" or "- Company - Careers"
        data.title = ogTitle.content.split(/\s*[|\-–—]\s*/)[0].trim();
      }
    }
    if (!data.company) {
      const ogSite = document.querySelector('meta[property="og:site_name"]');
      if (ogSite && ogSite.content) data.company = ogSite.content;
    }
    if (!data.description) {
      const ogDesc = document.querySelector('meta[property="og:description"]')
        || document.querySelector('meta[name="description"]');
      // Only use meta description if it's substantial (not just a tagline)
      if (ogDesc && ogDesc.content && ogDesc.content.length > 150) {
        data.description = ogDesc.content;
      }
    }

    // ── 3. Fill remaining gaps with DOM selectors ──
    if (!data.title) {
      const h1 = document.querySelector("h1");
      if (h1 && h1.textContent.trim()) data.title = h1.textContent.trim();
      else data.title = document.title.split(/\s*[|\-–—]\s*/)[0].trim();
    }

    if (!data.company) {
      // Try common ATS patterns
      const compSels = [
        "[class*='company-name']", "[class*='companyName']",
        "[class*='employer']", "[data-company]",
        "[class*='organization']",
      ];
      for (const sel of compSels) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim() && el.textContent.trim().length < 80) {
          data.company = el.textContent.trim(); break;
        }
      }
    }
    // Last resort: derive from hostname
    if (!data.company) {
      const h = window.location.hostname.replace("www.", "").replace("careers.", "").replace("jobs.", "").split(".")[0];
      data.company = h.charAt(0).toUpperCase() + h.slice(1);
    }

    if (!data.location) {
      // Try common selectors
      const locSels = [
        "[class*='location']", "[class*='Location']",
        "[data-location]", "[itemprop='jobLocation']",
        "[class*='workplace']",
      ];
      for (const sel of locSels) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim() && el.textContent.trim().length < 80) {
          data.location = el.textContent.trim(); break;
        }
      }
      // Text pattern fallback
      if (!data.location) {
        const h1 = document.querySelector("h1");
        if (h1) {
          let sib = h1.nextElementSibling;
          for (let i = 0; i < 5 && sib; i++) {
            const t = sib.textContent.trim();
            const m = t.match(/([A-Z][a-zA-Z\s]+,\s*[A-Z]{2})/)
              || t.match(/^(Virtual|Remote|United States|Worldwide|Hybrid)/i);
            if (m) { data.location = m[0].trim(); break; }
            sib = sib.nextElementSibling;
          }
        }
      }
    }

    // ── 4. Description — robust fallback chain ──
    if (!data.description || data.description.length < 150) {
      // Try ATS-specific selectors
      const descSels = [
        // Greenhouse
        "#content .content-intro",
        "#content",
        // Lever
        ".posting-page .content",
        "[class*='posting-description']",
        // Workday
        "[data-automation-id='jobPostingDescription']",
        // Ashby
        "[class*='ashby-job-posting-brief-description']",
        "._description_",
        // iCIMS
        ".iCIMS_JobContent",
        // SmartRecruiters
        ".job-sections",
        // Generic patterns
        "[class*='job-description']", "[class*='jobDescription']",
        "[id*='job-description']", "[id*='jobDescription']",
        "[class*='job-detail']", "[class*='jobDetail']",
        "[class*='posting-detail']",
        "[class*='description']",
        "[role='main'] section",
        "article",
        "main",
        "[role='main']",
      ];
      for (const sel of descSels) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 150) {
          data.description = el.innerText.trim();
          break;
        }
      }
    }

    // ── 5. Company URL fallback chain ──
    if (!data.company_url) {
      // Try company link in page header/nav (many ATS pages link to company site)
      const companyLinkSels = [
        "a[class*='company-name']", "a[class*='companyName']",
        "a[class*='company-link']", "a[class*='companyLink']",
        "a[class*='employer']",
        // Greenhouse: company logo links to company site
        ".company-header a[href]", ".banner a[href]",
        "a[class*='logo'][href]", "header a[href]",
      ];
      for (const sel of companyLinkSels) {
        const el = document.querySelector(sel);
        if (el && el.href
          && !el.href.includes(window.location.hostname)
          && !el.href.startsWith("javascript")
          && !el.href.includes("linkedin.com")) {
          data.company_url = el.href.split("?")[0];
          break;
        }
      }
    }
    // Final fallback: use current page URL (still useful for networking pipeline)
    if (!data.company_url) {
      data.company_url = window.location.href;
    }

    return data;
  }

  function extractJobData() { return isLinkedIn ? extractLinkedIn() : extractGeneric(); }

  // Keep message listener for popup fallback
  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.action === "getJobData") sendResponse(extractJobData());
    return true;
  });

  // ── Floating Widget ─────────────────────────────────────────

  const STYLES = `
    #jc-float {
      position: fixed;
      right: 16px;
      bottom: 80px;
      z-index: 2147483647;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    #jc-fab {
      width: 48px;
      height: 48px;
      border-radius: 14px;
      background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 16px rgba(67, 56, 202, 0.35);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    #jc-fab:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(67, 56, 202, 0.45);
    }
    #jc-fab svg { width: 24px; height: 24px; }
    #jc-panel {
      display: none;
      position: absolute;
      bottom: 56px;
      right: 0;
      width: 320px;
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(40px) saturate(1.6);
      -webkit-backdrop-filter: blur(40px) saturate(1.6);
      border: 1px solid rgba(255, 255, 255, 0.6);
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
      overflow: hidden;
    }
    #jc-float.open #jc-panel { display: block; }
    .jc-header {
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    .jc-logo { font-size: 15px; font-weight: 700; color: #1e293b; letter-spacing: -0.3px; }
    .jc-badge {
      font-size: 11px; font-weight: 600; color: #4338ca;
      background: rgba(224, 231, 255, 0.7); padding: 3px 10px;
      border-radius: 20px; border: 1px solid rgba(165, 180, 252, 0.25);
    }
    .jc-section { padding: 12px 16px; }
    .jc-section-label {
      font-size: 9px; font-weight: 700; color: #94a3b8;
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }
    .jc-detected {
      padding: 10px 12px; background: rgba(248, 250, 252, 0.8);
      border: 1px solid rgba(0,0,0,0.04); border-left: 3px solid #6366f1;
      border-radius: 8px;
    }
    .jc-det-company { font-size: 15px; font-weight: 700; color: #1e293b; }
    .jc-det-title { font-size: 12px; color: #475569; margin-top: 2px; }
    .jc-det-meta { font-size: 11px; color: #94a3b8; margin-top: 4px; }
    .jc-no-detect { font-size: 13px; color: #94a3b8; }
    .jc-btn-save {
      width: 100%; padding: 10px; border: none; border-radius: 10px; cursor: pointer;
      font-size: 13px; font-weight: 600; margin-top: 10px;
      color: #4338ca;
      background: linear-gradient(135deg, rgba(224,231,255,0.7), rgba(199,210,254,0.5));
      border: 1px solid rgba(165,180,252,0.3);
      box-shadow: 0 2px 8px rgba(99,102,241,0.1), inset 0 1px 0 rgba(255,255,255,0.6);
      transition: all 0.15s ease;
    }
    .jc-btn-save:hover:not(:disabled) { transform: translateY(-0.5px); box-shadow: 0 4px 14px rgba(99,102,241,0.18); }
    .jc-btn-save:disabled { opacity: 0.5; cursor: default; }
    .jc-btn-save.saved { background: linear-gradient(135deg, rgba(209,250,229,0.6), rgba(167,243,208,0.4)); color: #065f46; border-color: rgba(110,231,183,0.3); }
    .jc-divider { height: 1px; background: rgba(0,0,0,0.05); margin: 0; }
    .jc-batch-list {
      max-height: 160px; overflow-y: auto;
    }
    .jc-batch-list::-webkit-scrollbar { width: 4px; }
    .jc-batch-list::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 4px; }
    .jc-batch-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.03);
    }
    .jc-batch-item:last-child { border-bottom: none; }
    .jc-bi-company { font-size: 13px; font-weight: 600; color: #1e293b; }
    .jc-bi-role { font-size: 11px; color: #64748b; }
    .jc-bi-del {
      background: none; border: none; color: #cbd5e1; cursor: pointer;
      font-size: 16px; padding: 2px 6px; border-radius: 4px; transition: all 0.1s;
    }
    .jc-bi-del:hover { color: #ef4444; background: rgba(239,68,68,0.06); }
    .jc-empty { font-size: 12px; color: #94a3b8; text-align: center; padding: 12px 0; }
    .jc-footer {
      display: flex; gap: 0; border-top: 1px solid rgba(0,0,0,0.05);
    }
    .jc-footer-btn {
      flex: 1; padding: 10px; border: none; cursor: pointer;
      font-size: 12px; font-weight: 600; background: transparent;
      transition: background 0.1s;
    }
    .jc-footer-btn:first-child { border-right: 1px solid rgba(0,0,0,0.05); color: #065f46; }
    .jc-footer-btn:last-child { color: #4338ca; }
    .jc-footer-btn:hover { background: rgba(0,0,0,0.02); }
    .jc-footer-btn:disabled { opacity: 0.4; cursor: default; }
  `;

  // Inject styles
  const styleEl = document.createElement("style");
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  // Build widget DOM
  const root = document.createElement("div");
  root.id = "jc-float";
  root.innerHTML = `
    <div id="jc-panel">
      <div class="jc-header">
        <span class="jc-logo">JobCapture</span>
        <span class="jc-badge" id="jcBadge">0 in batch</span>
      </div>
      <div class="jc-section">
        <div class="jc-section-label">Detected on this page</div>
        <div id="jcDetected">
          <div class="jc-no-detect">No job detected</div>
        </div>
        <button class="jc-btn-save" id="jcSave" disabled>+ Save to Batch</button>
      </div>
      <div class="jc-divider"></div>
      <div class="jc-section">
        <div class="jc-section-label">Current Batch</div>
        <div class="jc-batch-list" id="jcBatchList">
          <div class="jc-empty">No jobs in batch yet</div>
        </div>
      </div>
      <div class="jc-footer">
        <button class="jc-footer-btn" id="jcFinish" disabled>Finish Batch</button>
        <button class="jc-footer-btn" id="jcDashboard">Dashboard →</button>
      </div>
    </div>
    <button id="jc-fab" title="JobCapture">
      <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
        <path d="M16 7V5a4 4 0 0 0-8 0v2"/>
        <circle cx="12" cy="14" r="2"/>
      </svg>
    </button>
  `;
  document.body.appendChild(root);

  // ── Widget logic ─────────────────────────────────────────────

  let currentJobData = null;
  let panelOpen = false;

  const fab = document.getElementById("jc-fab");

  // Toggle on click
  fab.addEventListener("click", (e) => {
    e.stopPropagation();
    panelOpen = !panelOpen;
    root.classList.toggle("open", panelOpen);
    if (panelOpen) { detectJob(); loadBatch(); }
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (panelOpen && !root.contains(e.target)) {
      panelOpen = false;
      root.classList.remove("open");
    }
  });

  // Hover open
  let hoverTimer = null;
  root.addEventListener("mouseenter", () => {
    clearTimeout(hoverTimer);
    if (!panelOpen) {
      panelOpen = true;
      root.classList.add("open");
      detectJob();
      loadBatch();
    }
  });
  root.addEventListener("mouseleave", () => {
    hoverTimer = setTimeout(() => {
      panelOpen = false;
      root.classList.remove("open");
    }, 400);
  });

  function detectJob() {
    const data = extractJobData();
    const container = document.getElementById("jcDetected");
    if (data.company || data.title) {
      currentJobData = data;
      container.innerHTML = `
        <div class="jc-detected">
          <div class="jc-det-company">${data.company || "Unknown Company"}</div>
          <div class="jc-det-title">${data.title || "Unknown Role"}</div>
          <div class="jc-det-meta">${data.location || "—"}</div>
        </div>`;
      document.getElementById("jcSave").disabled = false;
      document.getElementById("jcSave").textContent = "+ Save to Batch";
      document.getElementById("jcSave").classList.remove("saved");
    } else {
      currentJobData = null;
      container.innerHTML = '<div class="jc-no-detect">No job detected</div>';
      document.getElementById("jcSave").disabled = true;
    }
  }

  async function loadBatch() {
    try {
      const resp = await fetch(`${API}/api/jobs?status=active_batch`);
      const jobs = await resp.json();
      renderBatch(jobs);
    } catch (e) { console.error("JC: batch load failed", e); }
  }

  function renderBatch(jobs) {
    document.getElementById("jcBadge").textContent = `${jobs.length} in batch`;
    document.getElementById("jcFinish").disabled = jobs.length === 0;
    const list = document.getElementById("jcBatchList");
    if (jobs.length === 0) {
      list.innerHTML = '<div class="jc-empty">No jobs in batch yet</div>';
      return;
    }
    list.innerHTML = jobs.map(j => `
      <div class="jc-batch-item">
        <div>
          <div class="jc-bi-company">${j.company}</div>
          <div class="jc-bi-role">${j.title}</div>
        </div>
        <button class="jc-bi-del" data-id="${j.id}">×</button>
      </div>`).join("");
    list.querySelectorAll(".jc-bi-del").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await fetch(`${API}/api/jobs/${btn.dataset.id}`, { method: "DELETE" });
        loadBatch();
      });
    });
  }

  document.getElementById("jcSave").addEventListener("click", async () => {
    if (!currentJobData) return;
    const btn = document.getElementById("jcSave");
    btn.disabled = true;
    btn.textContent = "Saving...";
    try {
      await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentJobData),
      });
      btn.textContent = "Saved ✓";
      btn.classList.add("saved");
      loadBatch();
    } catch (e) {
      btn.textContent = "Error — retry";
      btn.disabled = false;
    }
  });

  document.getElementById("jcFinish").addEventListener("click", async () => {
    const btn = document.getElementById("jcFinish");
    btn.disabled = true;
    btn.textContent = "Finishing...";
    try {
      await fetch(`${API}/api/batches/finish`, { method: "POST" });
      btn.textContent = "Done ✓";
      loadBatch();
      setTimeout(() => { btn.textContent = "Finish Batch"; }, 2000);
    } catch (e) {
      btn.textContent = "Error";
      btn.disabled = false;
    }
  });

  document.getElementById("jcDashboard").addEventListener("click", () => {
    window.open("http://localhost:5173", "_blank");
  });

  // ── SPA Navigation Detection ────────────────────────────────
  // LinkedIn is a SPA — when user clicks a different job, the URL changes
  // but the content script doesn't re-run. Watch for URL changes and
  // DOM mutations to auto-refresh detection.

  if (isLinkedIn) {
    let lastUrl = window.location.href;

    // Poll for URL changes (pushState doesn't fire events we can listen to)
    setInterval(() => {
      if (window.location.href !== lastUrl) {
        lastUrl = window.location.href;
        // Wait for new content to render
        setTimeout(() => {
          if (panelOpen) detectJob();
        }, 1500);
      }
    }, 1000);

    // Also watch for DOM changes in the job detail area
    const observer = new MutationObserver(() => {
      if (panelOpen) detectJob();
    });

    // Observe the main content area for changes
    const watchTarget = document.querySelector("#main") || document.querySelector("main") || document.body;
    observer.observe(watchTarget, { childList: true, subtree: true });
  }
})();

// ── Application Questions Mini-Panel ─────────────────────────────
// Self-contained floating panel that only appears when free-text
// application questions are detected on the current page.
(function () {
  const API = (typeof JOBCAPTURE_CONFIG !== "undefined" && JOBCAPTURE_CONFIG.API_BASE_URL) || "http://localhost:8000";

  let panel = null;
  const state = {
    questions: [],
    slug: null,
    answers: null,
    pollTimer: null,
  };

  function makePanel() {
    const p = document.createElement("div");
    p.id = "jc-questions-panel";
    p.style.cssText = [
      "position:fixed", "bottom:20px", "right:20px", "z-index:2147483647",
      "width:320px", "padding:14px", "background:#ffffff",
      "border:1px solid rgba(0,0,0,0.08)", "border-radius:12px",
      "box-shadow:0 8px 28px rgba(15,23,42,0.18)",
      "font-family:system-ui,-apple-system,sans-serif",
      "font-size:13px", "color:#1e293b",
    ].join(";");
    p.innerHTML = `
      <div style="font-weight:700;font-size:13px;margin-bottom:4px;">JobCapture — Questions</div>
      <div id="jcqSubtle" style="font-size:11px;color:#64748b;margin-bottom:8px;"></div>
      <input id="jcqCompany" type="text" placeholder="Company name" style="width:100%;padding:7px;border:1px solid rgba(0,0,0,0.1);border-radius:7px;font-size:12px;box-sizing:border-box;margin-bottom:6px;" />
      <select id="jcqSlug" style="width:100%;padding:7px;border:1px solid rgba(0,0,0,0.1);border-radius:7px;font-size:12px;box-sizing:border-box;display:none;margin-bottom:6px;"></select>
      <button id="jcqCapture" style="width:100%;padding:8px;border:none;border-radius:8px;background:linear-gradient(135deg,#4338ca,#6366f1);color:#fff;font-weight:600;cursor:pointer;margin-bottom:4px;" disabled>Answer Questions</button>
      <button id="jcqFill" style="width:100%;padding:8px;border:none;border-radius:8px;background:#f1f5f9;color:#334155;font-weight:600;cursor:pointer;display:none;margin-bottom:4px;">Fill Answers</button>
      <div id="jcqStatus" style="font-size:11px;color:#475569;margin-top:6px;"></div>
      <div id="jcqPreview" style="max-height:160px;overflow-y:auto;margin-top:6px;"></div>
    `;
    document.body.appendChild(p);
    return p;
  }

  function $(id) { return panel.querySelector("#" + id); }

  function setStatus(msg, variant) {
    const el = $("jcqStatus");
    el.textContent = msg || "";
    el.style.color = variant === "ok" ? "#065f46" : variant === "warn" ? "#92400e" : "#475569";
  }

  async function tryMatch(name) {
    if (!name) return;
    let body;
    try {
      const resp = await fetch(`${API}/api/applications/match?company=${encodeURIComponent(name)}`);
      body = await resp.json();
    } catch (e) {
      setStatus("Backend unreachable.", "warn");
      return;
    }
    const dropdown = $("jcqSlug");
    const captureBtn = $("jcqCapture");
    if (!body.candidates || body.candidates.length === 0) {
      dropdown.style.display = "none";
      state.slug = null;
      captureBtn.disabled = true;
      setStatus(`No tailored resume for ${name}.`, "warn");
      return;
    }
    dropdown.style.display = "block";
    dropdown.replaceChildren(
      ...body.candidates.map((c) => {
        const opt = document.createElement("option");
        opt.value = c.slug;
        opt.textContent = c.slug;
        return opt;
      })
    );
    state.slug = body.candidates[0].slug;
    captureBtn.disabled = false;
    setStatus(body.candidates.length === 1 ? `Matched to ${state.slug}.` : `Multiple matches — pick one.`, "ok");
    checkForAnswers();
  }

  async function checkForAnswers() {
    if (!state.slug) return;
    clearTimeout(state.pollTimer);
    try {
      const resp = await fetch(`${API}/api/applications/${encodeURIComponent(state.slug)}/answers`);
      if (resp.status === 404) {
        $("jcqFill").style.display = "none";
        return;
      }
      if (!resp.ok) return;
      state.answers = await resp.json();
      renderPreview();
    } catch (e) { /* backend offline — ignore */ }
  }

  function renderPreview() {
    if (!state.answers || !state.answers.answers) return;
    $("jcqFill").style.display = "block";
    const container = $("jcqPreview");
    container.replaceChildren();
    state.answers.answers.forEach((a, idx) => {
      const item = document.createElement("div");
      item.style.cssText = "padding:6px;background:#f8fafc;border-radius:6px;margin-bottom:4px;";
      const label = document.createElement("div");
      label.style.cssText = "font-size:10px;color:#64748b;font-weight:600;margin-bottom:3px;";
      label.textContent = (a.question_text || `Question ${idx + 1}`).slice(0, 120);
      const textarea = document.createElement("textarea");
      textarea.style.cssText = "width:100%;min-height:50px;padding:5px;border:1px solid rgba(0,0,0,0.08);border-radius:5px;font-size:11px;font-family:inherit;box-sizing:border-box;";
      textarea.value = a.answer || "";
      textarea.addEventListener("input", () => {
        state.answers.answers[idx].answer = textarea.value;
      });
      item.appendChild(label);
      item.appendChild(textarea);
      container.appendChild(item);
    });
    setStatus(`${state.answers.answers.length} answers ready to fill.`, "ok");
  }

  function init() {
    if (!window.JC_QUESTIONS) return;
    state.questions = window.JC_QUESTIONS.detect();
    if (state.questions.length === 0) return;

    panel = makePanel();
    $("jcqSubtle").textContent = `${state.questions.length} question${state.questions.length > 1 ? "s" : ""} detected`;

    const companyInput = $("jcqCompany");
    let debounce;
    companyInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => tryMatch(companyInput.value.trim()), 400);
    });

    $("jcqSlug").addEventListener("change", (e) => {
      state.slug = e.target.value;
      checkForAnswers();
    });

    $("jcqCapture").addEventListener("click", async () => {
      if (!state.slug || state.questions.length === 0) return;
      const btn = $("jcqCapture");
      btn.disabled = true;
      btn.textContent = "Sending…";
      const payload = {
        company: companyInput.value.trim() || state.slug,
        role: "",
        application_url: window.location.href,
        company_match: { method: "auto", summary_file: "", script_file: "" },
        questions: state.questions,
      };
      try {
        const resp = await fetch(`${API}/api/applications/${encodeURIComponent(state.slug)}/questions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) throw new Error(await resp.text());
        btn.textContent = "Captured ✓";
        setStatus("Run /answer-questions in Claude Code. Polling…", "ok");
        let tries = 0;
        const poll = async () => {
          tries += 1;
          await checkForAnswers();
          if (!state.answers && tries < 60) {
            state.pollTimer = setTimeout(poll, 5000);
          }
        };
        poll();
      } catch (e) {
        btn.textContent = "Error — retry";
        btn.disabled = false;
        setStatus(String(e), "warn");
      }
    });

    $("jcqFill").addEventListener("click", () => {
      if (!state.answers || !window.JC_QUESTIONS) return;
      const enriched = state.answers.answers.map((a) => {
        const q = state.questions.find((dq) => dq.id === a.id);
        return { ...a, question_text: q ? q.text : null };
      });
      const { filled, unmatched } = window.JC_QUESTIONS.fill(enriched);
      if (unmatched.length === 0) {
        setStatus(`Filled ${filled.length} fields ✓`, "ok");
      } else {
        setStatus(`Filled ${filled.length}; ${unmatched.length} need manual paste.`, "warn");
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
