/**
 * TripMate - Bespoke Travel Intelligence Client
 * Luxury Editorial UX & Fully Responsive Mobile/Tablet/Desktop Behavior
 * Zero Emojis, Clean SVG Iconography, Timeline Parser, Touch-Friendly Navigation
 */

let currentThreadId = localStorage.getItem("travel_thread_id") || null;
let latestAnswerMarkdown = "";
let waitingForApproval = false;
let parsedDaysCount = 5;

// Clean specialist labels (Zero emojis)
const SPECIALIST_LABELS = {
  flight_agent: "Aviation & Route Intelligence",
  hotel_agent: "Hospitality & Curated Stays",
  weather_agent: "Meteorological & Climate Feed",
  budget_agent: "Expenditure & Feasibility",
  itinerary_agent: "Master Itinerary Synthesis"
};

// Curated high-resolution editorial destination images
const DESTINATION_IMAGES = {
  dubai: {
    url: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1400&q=85",
    caption: "Dubai & Abu Dhabi — Architectural marvels & Arabian desert dunes"
  },
  abu: {
    url: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1400&q=85",
    caption: "Dubai & Abu Dhabi — Architectural marvels & Arabian desert dunes"
  },
  tokyo: {
    url: "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=1400&q=85",
    caption: "Tokyo & Kyoto — Modern precision meets ancient temple serenity"
  },
  kyoto: {
    url: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1400&q=85",
    caption: "Kyoto & Historic Japan — Bamboo groves and centuries of culinary craft"
  },
  alps: {
    url: "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1400&q=85",
    caption: "Swiss Alps — Panoramic glaciers, alpine rail and mountain refuges"
  },
  swiss: {
    url: "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1400&q=85",
    caption: "Swiss Alps — Panoramic glaciers, alpine rail and mountain refuges"
  },
  amalfi: {
    url: "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=1400&q=85",
    caption: "Amalfi Coast & Rome — Mediterranean cliffs and classical antiquity"
  },
  rome: {
    url: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1400&q=85",
    caption: "Rome & Italian Heritage — Cobblestone piazzas, baroque art and culinary depth"
  },
  paris: {
    url: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1400&q=85",
    caption: "Paris — Haussmannian boulevards, world-class galleries and bistros"
  },
  default: {
    url: "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1400&q=85",
    caption: "Bespoke Itinerary Exploration — Thoughtfully curated journeys worldwide"
  }
};

/**
 * Mobile Navigation Drawer Toggle
 */
function toggleMobileNav(forceState) {
  const drawer = document.getElementById("mobileDrawer");
  const menuBtn = document.getElementById("mobileMenuBtn");
  if (!drawer) return;

  const isOpen = drawer.classList.contains("open");
  const shouldOpen = typeof forceState === "boolean" ? forceState : !isOpen;

  if (shouldOpen) {
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    if (menuBtn) menuBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  } else {
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    if (menuBtn) menuBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }
}

/**
 * Focus composer and scroll into view smoothly
 */
function focusComposer() {
  const destInput = document.getElementById("fieldDest");
  const composer = document.getElementById("plannerCard");
  if (composer) {
    composer.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  if (destInput) {
    setTimeout(() => { destInput.focus(); }, 300);
  }
}

/**
 * Scroll to approval / refinement desk
 */
function scrollToApproval() {
  const section = document.getElementById("approvalSection");
  if (section) {
    section.scrollIntoView({ behavior: "smooth", block: "center" });
    const feedbackInput = document.getElementById("approvalFeedback");
    if (feedbackInput) {
      setTimeout(() => { feedbackInput.focus(); }, 300);
    }
  }
}

/**
 * Switch editorial destination photography based on destination text
 */
function updateDestinationHero(destinationText) {
  const img = document.getElementById("destinationHeroImg");
  const caption = document.getElementById("destinationCaption");
  if (!img) return;

  const lower = (destinationText || "").toLowerCase();
  let match = DESTINATION_IMAGES.default;

  for (const key of Object.keys(DESTINATION_IMAGES)) {
    if (key !== "default" && lower.includes(key)) {
      match = DESTINATION_IMAGES[key];
      break;
    }
  }

  img.src = match.url;
  img.alt = match.caption;
  if (caption) {
    caption.textContent = match.caption;
  }
}

/**
 * Populate Composer fields from curated exemplar cards
 */
function applyExemplar(dest, days, style, interests, travelers, note) {
  const fieldDest = document.getElementById("fieldDest");
  const fieldDays = document.getElementById("fieldDays");
  const fieldStyle = document.getElementById("fieldStyle");
  const fieldInterests = document.getElementById("fieldInterests");
  const fieldTravelers = document.getElementById("fieldTravelers");
  const userInput = document.getElementById("userInput");

  if (fieldDest) fieldDest.value = dest;
  if (fieldDays) fieldDays.value = days;
  if (fieldStyle) fieldStyle.value = style;
  if (fieldInterests) fieldInterests.value = interests;
  if (fieldTravelers) fieldTravelers.value = travelers;
  if (userInput) {
    userInput.value = note;
    userInput.focus();
    userInput.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  updateDestinationHero(dest);
}

/**
 * Add suggestion feedback to the HITL confirmation textarea
 */
function addFeedback(text) {
  const feedbackInput = document.getElementById("approvalFeedback");
  if (!feedbackInput) return;
  const current = feedbackInput.value.trim();
  if (current) {
    feedbackInput.value = current + " " + text;
  } else {
    feedbackInput.value = text;
  }
  feedbackInput.focus();
}

/**
 * UI loading state management
 */
function setLoading(isLoading, mode = "draft") {
  const sendBtn = document.getElementById("sendBtn");
  const btnText = document.getElementById("btnText");
  const btnLoader = document.getElementById("btnLoader");
  const approveBtn = document.getElementById("approveBtn");
  const reviseBtn = document.getElementById("reviseBtn");

  if (sendBtn) sendBtn.disabled = isLoading;
  if (approveBtn) approveBtn.disabled = isLoading;
  if (reviseBtn) reviseBtn.disabled = isLoading;

  if (isLoading && mode === "draft") {
    if (btnText) btnText.textContent = "Curating Itinerary...";
    if (btnLoader) btnLoader.classList.remove("hidden");
  } else {
    if (btnText) btnText.textContent = "Create Itinerary";
    if (btnLoader) btnLoader.classList.add("hidden");
  }
}

/**
 * Show / hide error notices
 */
function showError(message) {
  const errorBox = document.getElementById("errorBox");
  if (!errorBox) return;
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideError() {
  const errorBox = document.getElementById("errorBox");
  if (!errorBox) return;
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

/**
 * Render standard Markdown to target element with mobile responsive table handling
 */
function renderMarkdown(element, markdown) {
  if (typeof marked !== "undefined") {
    element.innerHTML = marked.parse(markdown || "");
    
    // Automatically wrap all tables in responsive containers with swipe hint
    element.querySelectorAll("table").forEach((table) => {
      if (!table.parentElement.classList.contains("table-responsive-wrapper")) {
        const wrapper = document.createElement("div");
        wrapper.className = "table-responsive-wrapper";
        const hint = document.createElement("div");
        hint.className = "table-swipe-hint";
        hint.textContent = "Swipe horizontally to view full table details";
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(hint);
        wrapper.appendChild(table);
      }
    });
  } else {
    element.innerText = markdown || "";
  }
}

/**
 * Parse Markdown into structured vertical timeline cards
 */
function renderTimelineFromMarkdown(markdown) {
  const timelineContainer = document.getElementById("timelineContainer");
  const dayTabsContainer = document.getElementById("dayTabsContainer");
  if (!timelineContainer) return;

  timelineContainer.innerHTML = "";

  if (!markdown) {
    timelineContainer.classList.add("hidden");
    return;
  }

  // Enhanced regex to match all day heading variants (e.g. "### **Day 1 – ...**", "### Day 1: ...", "## Day 01 - ...")
  const dayRegex = /(?:^|\n)(?:#{1,4}\s*)?(?:\*\*)?\s*Day\s*(\d+)[\s\u00A0\u202F]*[:\-–—\.]*[\s\u00A0\u202F]*(.*?)(?:\*\*)?(?:\n|$)/gi;
  const matches = [...markdown.matchAll(dayRegex)];

  if (!matches || matches.length === 0) {
    timelineContainer.classList.add("hidden");
    return;
  }

  timelineContainer.classList.remove("hidden");
  const daysData = [];

  for (let i = 0; i < matches.length; i++) {
    const currentMatch = matches[i];
    const dayNum = parseInt(currentMatch[1], 10) || (i + 1);
    const rawTitle = (currentMatch[2] || "").replace(/[*_#]/g, "").trim();
    const dayTitle = rawTitle || `Exploration & Highlights`;
    const startIndex = currentMatch.index + currentMatch[0].length;
    const endIndex = (i + 1 < matches.length) ? matches[i + 1].index : markdown.length;
    const dayContent = markdown.slice(startIndex, endIndex).trim();

    const lines = dayContent.split("\n");
    const activities = [];
    let currentActivity = null;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (trimmed.startsWith("### Flight") || trimmed.startsWith("### Hotel") || trimmed.startsWith("### Budget") || trimmed.startsWith("## Final") || trimmed.startsWith("### 1.") || trimmed.startsWith("### 6.")) {
        break;
      }

      const timeMatch = trimmed.match(/^[-*•]?\s*(?:\*\*)?(\d{1,2}:\d{2}(?:\s*[AP]M)?|Morning|Afternoon|Evening|Night|Midday|Sunset|Dinner|Lunch)(?:\*\*)?[:\-–—\u00A0\s]*(.*)/i);
      
      if (timeMatch) {
        if (currentActivity) activities.push(currentActivity);
        const timeBadge = timeMatch[1].trim();
        const activityBody = timeMatch[2].trim().replace(/^\*\*|\*\*$/g, "");
        
        let title = activityBody;
        let desc = "";
        let loc = "";

        if (activityBody.includes(" — ")) {
          const parts = activityBody.split(" — ");
          title = parts[0];
          desc = parts.slice(1).join(" — ");
        } else if (activityBody.includes(" - ")) {
          const parts = activityBody.split(" - ");
          title = parts[0];
          desc = parts.slice(1).join(" - ");
        }

        currentActivity = {
          time: timeBadge,
          title: title.replace(/[*_#]/g, "").trim(),
          location: loc,
          description: desc.replace(/[*_]/g, "").trim(),
          meta: "Curated experience"
        };
      } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        if (currentActivity) activities.push(currentActivity);
        const cleanText = trimmed.replace(/^[-*]\s*/, "").replace(/[*_]/g, "").trim();
        currentActivity = {
          time: "Schedule",
          title: cleanText.length > 50 ? cleanText.slice(0, 48) + "..." : cleanText,
          location: "",
          description: cleanText.length > 50 ? cleanText : "",
          meta: "Recommended activity"
        };
      } else if (currentActivity && !trimmed.startsWith("#")) {
        currentActivity.description += (currentActivity.description ? " " : "") + trimmed.replace(/[*_]/g, "");
      }
    }

    if (currentActivity) activities.push(currentActivity);

    if (activities.length === 0) {
      activities.push({
        time: "All Day",
        title: dayTitle,
        location: "",
        description: dayContent.slice(0, 240).replace(/[#*_]/g, "") + "...",
        meta: "Planned itinerary"
      });
    }

    daysData.push({
      dayNum: dayNum,
      dayTitle: dayTitle.replace(/[*_]/g, ""),
      activities: activities
    });
  }

  parsedDaysCount = daysData.length;

  // Build Dynamic Day Selector Tabs
  if (dayTabsContainer) {
    let tabsHtml = `<button type="button" class="day-tab active" onclick="filterDay('all')">All Days</button>`;
    daysData.forEach((d) => {
      const padNum = d.dayNum < 10 ? `0${d.dayNum}` : `${d.dayNum}`;
      const shortTitle = d.dayTitle.length > 14 ? d.dayTitle.slice(0, 12) + "..." : d.dayTitle;
      tabsHtml += `<button type="button" class="day-tab" data-day-target="${d.dayNum}" onclick="filterDay(${d.dayNum})">${padNum} ${shortTitle}</button>`;
    });
    dayTabsContainer.innerHTML = tabsHtml;
  }

  // Build Vertical Timeline HTML
  let timelineHtml = "";
  daysData.forEach((d) => {
    const padNum = d.dayNum < 10 ? `0${d.dayNum}` : `${d.dayNum}`;
    timelineHtml += `
      <div class="day-group" data-day="${d.dayNum}">
        <div class="day-header">
          <span class="day-tag">Day ${padNum}</span>
          <h3 class="day-title">${d.dayTitle}</h3>
        </div>
        <div class="timeline-items">
    `;

    d.activities.forEach((act) => {
      timelineHtml += `
        <div class="timeline-item">
          <div class="timeline-dot"></div>
          <div class="timeline-time">${act.time}</div>
          <div class="timeline-content">
            <div class="activity-title">${act.title}</div>
            ${act.location ? `<div class="activity-location">${act.location}</div>` : ""}
            ${act.description ? `<div class="activity-description">${act.description}</div>` : ""}
            ${act.meta ? `<div class="activity-meta"><span>${act.meta}</span></div>` : ""}
          </div>
        </div>
      `;
    });

    timelineHtml += `
        </div>
      </div>
    `;
  });

  timelineContainer.innerHTML = timelineHtml;
}

/**
 * Filter timeline day visibility and center active tab in horizontal scroll
 */
function filterDay(dayNumber) {
  const tabs = document.querySelectorAll(".day-tab");
  tabs.forEach((tab) => {
    const target = tab.getAttribute("data-day-target");
    if (dayNumber === "all" && !target) {
      tab.classList.add("active");
      tab.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    } else if (target === String(dayNumber)) {
      tab.classList.add("active");
      tab.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    } else {
      tab.classList.remove("active");
    }
  });

  const dayGroups = document.querySelectorAll(".day-group");
  dayGroups.forEach((group) => {
    const groupDay = group.getAttribute("data-day");
    if (dayNumber === "all" || groupDay === String(dayNumber)) {
      group.style.display = "block";
    } else {
      group.style.display = "none";
    }
  });
}

/**
 * Display Workflow Intelligence and Routing
 */
function showWorkflow(data) {
  const section = document.getElementById("workflowSection");
  const reasoning = document.getElementById("supervisorReasoning");
  const chips = document.getElementById("agentChips");
  const guardrailBadge = document.getElementById("guardrailBadge");

  if (reasoning) {
    reasoning.textContent = data.supervisor_reasoning || "Executive routing pipeline established across regional specialists.";
  }

  if (chips) {
    chips.innerHTML = "";
    (data.selected_agents || []).forEach((agent) => {
      const chip = document.createElement("span");
      chip.className = "specialist-tag";
      chip.textContent = SPECIALIST_LABELS[agent] || agent.replace(/_/g, " ").toUpperCase();
      chips.appendChild(chip);
    });
  }

  if (guardrailBadge) {
    if (data.guardrail_allowed === false) {
      guardrailBadge.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        <span>Policy Declined</span>
      `;
      guardrailBadge.classList.add("blocked");
    } else {
      guardrailBadge.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span>Policy Verified</span>
      `;
      guardrailBadge.classList.remove("blocked");
    }
  }

  if (section) section.classList.remove("hidden");
}

/**
 * Update Quick Summary Metric Strip
 */
function updateSummaryMetrics(dest, days, style) {
  const metricDays = document.getElementById("metricDays");
  const metricCities = document.getElementById("metricCities");
  const metricHotels = document.getElementById("metricHotels");
  const metricExp = document.getElementById("metricExp");
  const metricBudget = document.getElementById("metricBudget");
  const metaLine = document.getElementById("itineraryMetaLine");

  const dayMatch = (days || "").match(/\d+/);
  const numDays = dayMatch ? parseInt(dayMatch[0], 10) : 5;

  if (metricDays) metricDays.textContent = numDays;

  const citiesCount = (dest || "").split(/[,&+/]+/).filter(Boolean).length || 2;
  if (metricCities) metricCities.textContent = Math.min(citiesCount, 4);

  const hotelCount = Math.max(1, Math.ceil(numDays / 2.2));
  if (metricHotels) metricHotels.textContent = hotelCount;

  if (metricExp) metricExp.textContent = Math.round(numDays * 2.5);

  let budgetEstimate = `EST. $${numDays * 450}`;
  if ((style || "").toLowerCase().includes("luxury")) {
    budgetEstimate = `EST. $${numDays * 850}`;
  } else if ((style || "").toLowerCase().includes("boutique")) {
    budgetEstimate = `EST. $${numDays * 550}`;
  }
  if (metricBudget) metricBudget.textContent = budgetEstimate;

  if (metaLine) {
    metaLine.textContent = `${numDays} days · ${dest || "Curated Itinerary"} · ${style || "Luxury"}`;
  }
}

/**
 * Display Master Itinerary Results
 */
function showResult(answer, threadId, isDraft = false) {
  latestAnswerMarkdown = answer || "";

  const resultSection = document.getElementById("resultSection");
  const resultBox = document.getElementById("resultBox");
  const threadInfo = document.getElementById("threadInfo");
  const resultTitle = document.getElementById("resultTitle");
  const resultSubtitle = document.getElementById("resultSubtitle");

  renderTimelineFromMarkdown(latestAnswerMarkdown);
  renderMarkdown(resultBox, latestAnswerMarkdown);

  if (threadInfo) {
    threadInfo.textContent = `Reference ID: ${threadId || "EXP-" + Date.now().toString(36).toUpperCase()}`;
  }

  if (isDraft) {
    if (resultSubtitle) resultSubtitle.textContent = "PRELIMINARY DOSSIER";
    if (resultTitle) resultTitle.textContent = "Draft Itinerary (Under Review)";
  } else {
    if (resultSubtitle) resultSubtitle.textContent = "CONFIRMED MASTER PLAN";
    if (resultTitle) resultTitle.textContent = "Your Bespoke Travel Itinerary";
  }

  if (resultSection) {
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

/**
 * Display HITL Review / Refinement Section
 */
function showApproval(data) {
  waitingForApproval = true;
  const section = document.getElementById("approvalSection");
  const approvalRequest = document.getElementById("approvalRequest");
  const stickyBar = document.getElementById("mobileStickyBar");

  if (approvalRequest) {
    approvalRequest.textContent =
      data.approval_request ||
      "Our concierge specialists have assembled an initial travel draft. Review the schedule above and choose to confirm as final, or specify custom adjustments.";
  }
  if (section) {
    section.classList.remove("hidden");
    section.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  if (stickyBar) {
    stickyBar.classList.remove("hidden");
  }
}

function hideApproval() {
  waitingForApproval = false;
  const section = document.getElementById("approvalSection");
  const stickyBar = document.getElementById("mobileStickyBar");
  if (section) section.classList.add("hidden");
  if (stickyBar) stickyBar.classList.add("hidden");
  const feedbackInput = document.getElementById("approvalFeedback");
  if (feedbackInput) feedbackInput.value = "";
}

/**
 * Submit Travel Brief to API
 */
async function sendMessage() {
  hideError();

  if (waitingForApproval) {
    showError("Please confirm or request adjustments on the current travel draft before submitting a new brief.");
    return;
  }

  const fieldDest = document.getElementById("fieldDest")?.value.trim() || "";
  const fieldDays = document.getElementById("fieldDays")?.value.trim() || "";
  const fieldStyle = document.getElementById("fieldStyle")?.value.trim() || "";
  const fieldInterests = document.getElementById("fieldInterests")?.value.trim() || "";
  const fieldTravelers = document.getElementById("fieldTravelers")?.value.trim() || "";
  const userInput = document.getElementById("userInput")?.value.trim() || "";

  if (!fieldDest && !userInput) {
    showError("Please specify your desired destination or trip brief.");
    return;
  }

  const insightPace = document.getElementById("insightPace");
  const insightStyle = document.getElementById("insightStyle");
  const insightInterests = document.getElementById("insightInterests");
  const insightApproach = document.getElementById("insightApproach");

  if (insightPace) insightPace.textContent = fieldStyle.includes("Relaxed") ? "Unhurried & Immersive" : "Balanced & Engaging";
  if (insightStyle) insightStyle.textContent = fieldStyle || "Luxury";
  if (insightInterests) insightInterests.textContent = fieldInterests || "Culture · Cuisine · Heritage";
  if (insightApproach) insightApproach.textContent = "Curated Specialist Intel";

  updateDestinationHero(fieldDest);
  updateSummaryMetrics(fieldDest, fieldDays, fieldStyle);

  let combinedMessage = userInput;
  if (!combinedMessage || combinedMessage.length < 20) {
    combinedMessage = `Plan a ${fieldDays || "5-day"} ${fieldStyle || "Luxury"} journey to ${fieldDest || "Dubai"}. Interests: ${fieldInterests || "Culture and Food"}. Travelers: ${fieldTravelers || "2 adults"}. ${userInput}`;
  } else if (!combinedMessage.toLowerCase().includes(fieldDest.toLowerCase())) {
    combinedMessage = `Destination: ${fieldDest}. Duration: ${fieldDays}. Style: ${fieldStyle}. Interests: ${fieldInterests}. Travelers: ${fieldTravelers}.\n\nDetails: ${combinedMessage}`;
  }

  setLoading(true, "draft");

  try {
    const response = await fetch("/api/travel", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: combinedMessage,
        thread_id: currentThreadId
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "An error occurred while generating the itinerary.");
    }

    currentThreadId = data.thread_id;
    localStorage.setItem("travel_thread_id", currentThreadId);

    showWorkflow(data);

    if (data.requires_approval) {
      showResult(data.itinerary || data.answer, data.thread_id, true);
      showApproval(data);
    } else {
      hideApproval();
      showResult(data.answer, data.thread_id, false);
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false, "draft");
  }
}

/**
 * Submit HITL Confirmation or Revision Request
 */
async function submitApproval(approved) {
  hideError();

  if (!currentThreadId || !waitingForApproval) {
    showError("There is no active itinerary draft awaiting confirmation.");
    return;
  }

  const feedbackInput = document.getElementById("approvalFeedback");
  const feedback = feedbackInput ? feedbackInput.value.trim() : "";

  if (!approved && !feedback) {
    showError("Please specify your desired adjustments before requesting a revision.");
    if (feedbackInput) {
      feedbackInput.focus();
      feedbackInput.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return;
  }

  setLoading(true, "approval");

  try {
    const response = await fetch("/api/travel/approve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        thread_id: currentThreadId,
        approved: approved,
        feedback: feedback
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Could not finalize the itinerary.");
    }

    showWorkflow(data);

    if (data.requires_approval) {
      showResult(data.itinerary || data.answer, data.thread_id, true);
      showApproval(data);
    } else {
      hideApproval();
      showResult(data.answer, data.thread_id, false);
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false, "approval");
  }
}

/**
 * Copy formatted itinerary text to clipboard
 */
function copyResult() {
  const resultBox = document.getElementById("resultBox");
  const text = resultBox ? resultBox.innerText : "";

  if (!text) return;

  navigator.clipboard.writeText(text)
    .then(() => {
      const copyBtn = document.querySelector(".copy-btn span");
      if (copyBtn) {
        const original = copyBtn.textContent;
        copyBtn.textContent = "Brief Copied";
        setTimeout(() => { copyBtn.textContent = original; }, 1800);
      }
    })
    .catch(() => {
      showError("Unable to copy to clipboard.");
    });
}

/**
 * Export high-resolution editorial PDF
 */
function downloadPDF() {
  const pdfContent = document.getElementById("pdfContent");

  if (!latestAnswerMarkdown || !pdfContent) {
    showError("No itinerary available for export.");
    return;
  }

  const downloadBtn = document.querySelector(".download-btn span");
  const originalText = downloadBtn ? downloadBtn.textContent : "Export PDF";
  if (downloadBtn) downloadBtn.textContent = "Generating...";

  const options = {
    margin: [0.5, 0.5, 0.5, 0.5],
    filename: `TripMate-Itinerary-${currentThreadId || "Client"}.pdf`,
    image: { type: "jpeg", quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true, backgroundColor: "#F7F5F0" },
    jsPDF: { unit: "in", format: "a4", orientation: "portrait" },
    pagebreak: { mode: ["avoid-all", "css", "legacy"] }
  };

  html2pdf()
    .set(options)
    .from(pdfContent)
    .save()
    .then(() => {
      if (downloadBtn) downloadBtn.textContent = originalText;
    })
    .catch((err) => {
      if (downloadBtn) downloadBtn.textContent = originalText;
      showError("PDF export encountered an issue: " + err.message);
    });
}

/**
 * Global Keyboard Shortcuts & Event Listeners
 */
document.addEventListener("keydown", function(event) {
  if (event.ctrlKey && event.key === "Enter") {
    sendMessage();
  }
  if (event.key === "Escape") {
    toggleMobileNav(false);
  }
});

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
  const fieldDest = document.getElementById("fieldDest");
  if (fieldDest && fieldDest.value) {
    updateDestinationHero(fieldDest.value);
  }
});
