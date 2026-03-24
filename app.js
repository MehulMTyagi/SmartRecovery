const ADMIN_EMAIL = "s24bcau0044@bennett.edu.in";

const state = {
  currentUser: null,
  users: [],
  lostItems: [],
  foundItems: [],
  discoverableFoundItems: [],
  claims: [],
  allClaims: [],
  matches: [],
  suspicious: [],
  pendingClaims: [],
  config: {
    pickupPoint: "Official Lost and Found Office, Bennett University Campus",
  },
  currentPage: "home",
};

const app = document.querySelector("#app");
const toast = document.querySelector("#toast");

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => toast.classList.add("hidden"), 2400);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(dateInput) {
  if (!dateInput) return "Not provided";
  const date = new Date(dateInput);
  if (Number.isNaN(date.getTime())) return dateInput;
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderEmpty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function isAdmin(user) {
  return Boolean(user) && user.email.toLowerCase() === ADMIN_EMAIL;
}

function getUserById(userId) {
  return state.users.find((user) => user.id === userId) || null;
}

function claimsForCurrentUser() {
  return state.claims || [];
}

function approvedClaimForItem(foundItemId) {
  return state.allClaims.find((claim) => claim.foundItemId === foundItemId && claim.status === "approved") || null;
}

async function fileToDataUrl(file) {
  if (!file || file.size === 0) return "";
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function setState(payload) {
  state.currentUser = payload.currentUser || null;
  state.users = payload.users || [];
  state.lostItems = payload.lostItems || [];
  state.foundItems = payload.foundItems || [];
  state.discoverableFoundItems = payload.discoverableFoundItems || payload.foundItems || [];
  state.claims = payload.claims || [];
  state.allClaims = payload.allClaims || [];
  state.matches = payload.matches || [];
  state.suspicious = payload.suspicious || [];
  state.pendingClaims = payload.pendingClaims || [];
  state.config = payload.config || state.config;
}

async function refreshState() {
  try {
    const payload = await api("/api/state", { method: "GET", headers: {} });
    setState(payload);
    render();
  } catch (error) {
    state.currentUser = null;
    render();
  }
}

function itemCard(item, type, currentUser, showClaimBox = false, showDeleteButton = false) {
  const image = item.imageData ? `<img src="${item.imageData}" alt="${escapeHtml(item.itemName)}">` : "";
  const approvedClaim = type === "found" ? approvedClaimForItem(item.id) : null;
  const existingClaim = claimsForCurrentUser().find(
    (claim) => claim.userId === currentUser.id && claim.foundItemId === item.id
  );
  const claimBlocked = Boolean(existingClaim || approvedClaim);
  const pickupHint =
    approvedClaim && item.userId === currentUser.id
      ? `<p class="muted compact">Hand this item to ${escapeHtml(state.config.pickupPoint)} after approval.</p>`
      : "";
  const claimBox = showClaimBox
    ? `
      <div class="inline-proof">
        <textarea data-proof-for="${item.id}" rows="3" placeholder="Add identifying details or proof before claiming"></textarea>
        <button data-claim-btn="${item.id}" ${claimBlocked ? "disabled" : ""}>
          ${existingClaim ? "Claim submitted" : approvedClaim ? "Already approved" : "Claim this item"}
        </button>
      </div>
    `
    : "";
  const deleteButton = showDeleteButton
    ? `<div class="action-row"><button class="danger" data-delete-item="${type}:${item.id}">Delete ${type} item</button></div>`
    : "";

  return `
    <article class="item-card">
      <div class="card-header">
        <div>
          <h4>${escapeHtml(item.itemName)}</h4>
          <p class="muted compact">${escapeHtml(item.description)}</p>
        </div>
        <span class="badge ${escapeHtml(item.status || "pending")}">${escapeHtml(item.status || "pending")}</span>
      </div>
      <div class="meta">
        <span>${type === "lost" ? "Lost at" : "Found at"} ${escapeHtml(item.location)}</span>
        <span>${formatDate(item.dateTime)}</span>
      </div>
      ${image}
      ${pickupHint}
      ${claimBox}
      ${deleteButton}
    </article>
  `;
}

function claimCard(claim, currentUser) {
  const foundItem = state.foundItems.find((item) => item.id === claim.foundItemId);
  const founder = foundItem ? getUserById(foundItem.userId) : null;
  const isClaimant = claim.userId === currentUser.id;
  const isFounder = founder?.id === currentUser.id;
  const roleLabel = isFounder && !isClaimant ? "Founder handover task" : "Your claim";

  const actionButton =
    claim.status === "approved" && isFounder && claim.handoverStatus === "awaiting_founder_dropoff"
      ? `<button data-dropoff-claim="${claim.id}" class="secondary">Mark dropped at office</button>`
      : claim.status === "approved" && isClaimant && claim.handoverStatus === "ready_for_pickup"
        ? `<button data-collected-claim="${claim.id}" class="secondary">Mark collected</button>`
        : "";

  return `
    <article class="claim-card">
      <div class="card-header">
        <div>
          <h4>${escapeHtml(foundItem?.itemName || "Claimed item")}</h4>
          <p class="muted compact">${escapeHtml(roleLabel)}</p>
          <p class="muted compact">${escapeHtml(claim.proof)}</p>
        </div>
        <span class="badge ${escapeHtml(claim.status)}">${escapeHtml(claim.status)}</span>
      </div>
      <div class="meta">
        <span>${formatDate(claim.createdAt)}</span>
        <span>${escapeHtml(claim.handoverStatusLabel || "Awaiting review")}</span>
      </div>
      ${claim.adminNotes ? `<p class="muted compact">Admin note: ${escapeHtml(claim.adminNotes)}</p>` : ""}
      ${
        claim.status === "approved"
          ? `<div class="pickup-box">
              <p><strong>Pickup point:</strong> ${escapeHtml(claim.pickupPoint)}</p>
              ${isClaimant ? `<p><strong>Pickup token:</strong> ${escapeHtml(claim.pickupToken)}</p>` : ""}
              ${claim.founderDroppedAt ? `<p><strong>Dropped:</strong> ${formatDate(claim.founderDroppedAt)}</p>` : ""}
              ${claim.collectedAt ? `<p><strong>Collected:</strong> ${formatDate(claim.collectedAt)}</p>` : ""}
              ${actionButton}
            </div>`
          : ""
      }
    </article>
  `;
}

function homeCard(title, text, nav, stat) {
  const imageMap = {
    "report-lost": "/assets/report-lost.svg",
    "report-found": "/assets/report-found.svg",
    "campus-discoveries": "/assets/campus-discoveries.svg",
    "your-lost": "/assets/your-lost.svg",
    "your-discoveries": "/assets/your-discoveries.svg",
    matches: "/assets/matches.svg",
    claims: "/assets/claims.svg",
    admin: "/assets/admin.svg",
  };

  return `
    <button class="home-card image-card" data-nav="${nav}" style="--card-image: url('${imageMap[nav]}')">
      <span class="home-card-overlay"></span>
      <span class="home-card-content">
        <span class="section-tag">${escapeHtml(stat)}</span>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(text)}</span>
      </span>
    </button>
  `;
}

function pageHeader(kicker, title, text) {
  return `
    <section class="page-header card">
      <p class="section-tag">${escapeHtml(kicker)}</p>
      <h3>${escapeHtml(title)}</h3>
      <p class="muted">${escapeHtml(text)}</p>
    </section>
  `;
}

function renderLostForm() {
  return `
    ${pageHeader("Report Lost Item", "Tell us what went missing", "Add details, location, time, and image so the system can start matching immediately.")}
    <section class="page-grid">
      <article class="card">
        <form id="lost-item-form" class="stacked-form">
          <label>Item name<input name="itemName" type="text" placeholder="Black backpack" required></label>
          <label>Description<textarea name="description" rows="4" placeholder="Brand, stickers, unique contents, serial marks..." required></textarea></label>
          <label>Lost location<input name="location" type="text" placeholder="Library, 2nd floor" required></label>
          <label>Date and time<input name="dateTime" type="datetime-local" required></label>
          <label>Image<input name="image" type="file" accept="image/*"></label>
          <button type="submit">Submit lost item</button>
        </form>
      </article>
      <article class="card helper-card">
        <h4>What helps most</h4>
        <p class="muted">Mention stickers, scratches, brands, contents, or any feature only the real owner would know.</p>
      </article>
    </section>
  `;
}

function renderFoundForm() {
  return `
    ${pageHeader("Report Found Item", "Log something you found on campus", "A clear report helps the right owner find it faster without exposing private contact details.")}
    <section class="page-grid">
      <article class="card">
        <form id="found-item-form" class="stacked-form">
          <label>Item name<input name="itemName" type="text" placeholder="Apple Watch" required></label>
          <label>Description<textarea name="description" rows="4" placeholder="Color, brand, visible marks, where it was discovered..." required></textarea></label>
          <label>Found location<input name="location" type="text" placeholder="Engineering block lobby" required></label>
          <label>Date and time<input name="dateTime" type="datetime-local" required></label>
          <label>Image<input name="image" type="file" accept="image/*"></label>
          <button type="submit">Submit found item</button>
        </form>
      </article>
      <article class="card helper-card">
        <h4>After approval</h4>
        <p class="muted">If admin approves a claim, the handoff happens through ${escapeHtml(state.config.pickupPoint)}.</p>
      </article>
    </section>
  `;
}

function renderListPage(kicker, title, text, html) {
  return `
    ${pageHeader(kicker, title, text)}
    <section class="page-grid single-column">
      <article class="card">
        <div class="list-block">${html}</div>
      </article>
    </section>
  `;
}

function renderHomePage(user) {
  const userLostItems = state.lostItems.filter((item) => item.userId === user.id);
  const userFoundItems = state.foundItems.filter((item) => item.userId === user.id);
  const adminUser = isAdmin(user);
  return `
    ${pageHeader("Home", "Choose where you want to work", "Each section now has its own focused page so you can move through the recovery flow without clutter.")}
    <section class="home-grid">
      ${adminUser ? "" : homeCard("Report a lost item", "Start a recovery request with full details.", "report-lost", `${userLostItems.length} reports`)}
      ${adminUser ? "" : homeCard("Report a found item", "Log something discovered on campus.", "report-found", `${userFoundItems.length} discoveries`)}
      ${homeCard("Campus discoveries", "Browse found items once access is unlocked.", "campus-discoveries", `${state.discoverableFoundItems.length} visible`)}
      ${homeCard("Your lost items", "Review everything you have reported as missing.", "your-lost", `${userLostItems.length} active`)}
      ${homeCard("Your discoveries", "See the items you personally found.", "your-discoveries", `${userFoundItems.length} posted`)}
      ${homeCard("Suggested matches", "Open the best possible matches first.", "matches", `${state.matches.length} matches`)}
      ${homeCard("Claims and pickup", "Track approvals, office drop-offs, and collection.", "claims", `${claimsForCurrentUser().length} claims`)}
      ${isAdmin(user) ? homeCard("Admin panel", "Approve claims and watch suspicious activity.", "admin", `${state.pendingClaims.length} pending`) : ""}
    </section>
  `;
}

function renderPageContent(user) {
  const userLostItems = state.lostItems
    .filter((item) => item.userId === user.id)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  const userFoundItems = state.foundItems
    .filter((item) => item.userId === user.id)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  const visibleFoundItems = [...state.discoverableFoundItems].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  const canViewFoundItems = userLostItems.length > 0;
  const adminUser = isAdmin(user);

  if (adminUser && (state.currentPage === "report-lost" || state.currentPage === "report-found")) {
    state.currentPage = "admin";
  }

  switch (state.currentPage) {
    case "report-lost":
      return renderLostForm();
    case "report-found":
      return renderFoundForm();
    case "campus-discoveries":
      return renderListPage(
        "Campus Discoveries",
        "Browse found items on campus",
        canViewFoundItems
          ? "Claim only when you can provide enough proof. Approved handoff happens through the official lost and found office."
          : "Submit at least one lost-item report to unlock the full discoveries list.",
        visibleFoundItems.length
          ? visibleFoundItems.map((item) => itemCard(item, "found", user, canViewFoundItems)).join("")
          : renderEmpty(canViewFoundItems ? "No found items have been reported yet." : "Found items stay hidden until you file a lost report.")
      );
    case "your-lost":
      return renderListPage(
        "Your Lost Items",
        "Everything you reported missing",
        "Use this page to review what you have submitted and compare it against matches.",
        userLostItems.length
          ? userLostItems.map((item) => itemCard(item, "lost", user, false, true)).join("")
          : renderEmpty("You have not reported any lost items yet.")
      );
    case "your-discoveries":
      return renderListPage(
        "Your Discoveries",
        "Items you found on campus",
        "When admin approves a claim, you will hand the item over through the official office workflow.",
        userFoundItems.length
          ? userFoundItems.map((item) => itemCard(item, "found", user, false, true)).join("")
          : renderEmpty("You have not submitted any found items yet.")
      );
    case "matches":
      return renderListPage(
        "Suggested Matches",
        "Likely connections between lost and found items",
        "These are generated automatically from item names, descriptions, and location similarity.",
        state.matches.length
          ? state.matches
              .map(
                (match) => {
                  const existingClaim = claimsForCurrentUser().find(
                    (claim) => claim.userId === user.id && claim.foundItemId === match.foundItem.id
                  );
                  const approved = approvedClaimForItem(match.foundItem.id);
                  const claimBlocked = Boolean(existingClaim || approved);
                  return `
                    <article class="match-card">
                      <div class="card-header">
                        <div>
                          <h4>${escapeHtml(match.lostItem.itemName)} <-> ${escapeHtml(match.foundItem.itemName)}</h4>
                          <p class="muted compact">Possible match based on title overlap, keywords, and location similarity.</p>
                        </div>
                        <span class="badge approved">${match.score}% match</span>
                      </div>
                      <div class="meta">
                        <span>Lost: ${escapeHtml(match.lostItem.location)}</span>
                        <span>Found: ${escapeHtml(match.foundItem.location)}</span>
                      </div>
                      <p class="muted compact">${escapeHtml(match.foundItem.description)}</p>
                      <div class="inline-proof">
                        <textarea data-proof-for="${match.foundItem.id}" rows="3" placeholder="Add identifying details or proof before claiming"></textarea>
                        <button data-claim-btn="${match.foundItem.id}" ${claimBlocked ? "disabled" : ""}>
                          ${existingClaim ? "Claim submitted" : approved ? "Already approved" : "Claim this matched item"}
                        </button>
                      </div>
                    </article>
                  `;
                }
              )
              .join("")
          : renderEmpty("No strong matches yet.")
      );
    case "claims":
      return renderListPage(
        "Claims & Pickup",
        "Track verification and office handoff",
        `Every approved claim moves through ${state.config.pickupPoint}.`,
        claimsForCurrentUser().length
          ? claimsForCurrentUser().map((claim) => claimCard(claim, user)).join("")
          : renderEmpty("You have no claims yet.")
      );
    case "admin":
      if (!isAdmin(user)) {
        state.currentPage = "home";
        return renderHomePage(user);
      }
      return `
        ${pageHeader("Admin Panel", "Approve claims and review unusual activity", "This page is only visible to the Smart Recover admin account.")}
        <section class="page-grid">
          <article class="card">
            <div class="section-heading"><div><p class="section-tag">Pending claims</p><h3>Needs review</h3></div></div>
            <div class="list-block">
              ${
                state.pendingClaims.length
                  ? state.pendingClaims
                      .map((claim) => {
                        const claimUser = getUserById(claim.userId);
                        const foundItem = state.foundItems.find((item) => item.id === claim.foundItemId);
                        return `
                          <article class="claim-card">
                            <div class="card-header">
                              <div>
                                <h4>${escapeHtml(foundItem?.itemName || "Unknown item")}</h4>
                                <p class="muted compact">${escapeHtml(claimUser?.name || "Unknown user")} submitted proof: ${escapeHtml(claim.proof)}</p>
                              </div>
                              <span class="badge pending">pending</span>
                            </div>
                            <div class="meta">
                              <span>${escapeHtml(claimUser?.email || "No email")}</span>
                              <span>${formatDate(claim.createdAt)}</span>
                            </div>
                            <div class="action-row">
                              <button class="secondary" data-approve-claim="${claim.id}">Approve</button>
                              <button class="danger" data-reject-claim="${claim.id}">Reject</button>
                            </div>
                          </article>
                        `;
                      })
                      .join("")
                  : renderEmpty("There are no pending claims right now.")
              }
            </div>
          </article>
          <article class="card">
            <div class="section-heading"><div><p class="section-tag">Suspicious activity</p><h3>Flagged accounts</h3></div></div>
            <div class="list-block">
              ${
                state.suspicious.length
                  ? state.suspicious
                      .map(
                        (entry) => `
                          <article class="alert-card">
                            <h4>${escapeHtml(entry.user.name)}</h4>
                            <p class="muted compact">${escapeHtml(entry.user.email)}</p>
                            <p>${escapeHtml(entry.flags.join(" | "))}</p>
                          </article>
                        `
                      )
                      .join("")
                  : renderEmpty("No suspicious activity has been flagged.")
              }
            </div>
          </article>
        </section>
      `;
    default:
      return renderHomePage(user);
  }
}

function renderStats(user) {
  const userLostItems = state.lostItems.filter((item) => item.userId === user.id).length;
  const userFoundItems = state.foundItems.filter((item) => item.userId === user.id).length;
  const cards = [
    ["Lost reports", userLostItems],
    ["Found reports", userFoundItems],
    ["Matches", state.matches.length],
    ["Claims", claimsForCurrentUser().length],
  ];

  document.querySelector("#stats-grid").innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="stat-card">
          <p class="section-tag">${escapeHtml(label)}</p>
          <strong>${escapeHtml(value)}</strong>
        </article>
      `
    )
    .join("");
}

function renderGuestView() {
  app.innerHTML = document.querySelector("#guest-template").innerHTML;
  document.body.classList.add("guest-mode");

  const loginForm = document.querySelector("#login-form");
  const signupForm = document.querySelector("#signup-form");
  const signinSwitch = document.querySelector("#signin-switch");

  document.querySelectorAll("[data-auth-switch]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.getAttribute("data-auth-switch");
      const showSignup = target === "signup";
      loginForm.classList.toggle("hidden", showSignup);
      signupForm.classList.toggle("hidden", !showSignup);
      signinSwitch.classList.toggle("hidden", !showSignup);
      document.querySelector(".auth-panel-intro h2").textContent = showSignup ? "Create account" : "Login";
      document.querySelector(".auth-panel-intro .muted").textContent = showSignup
        ? "Create your verified Bennett University account to report or recover items."
        : "Use your Bennett University email ID to access Smart Recover.";
    });
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    try {
      const payload = await api("/api/signup", {
        method: "POST",
        body: JSON.stringify({
          name: formData.get("name").trim(),
          email: formData.get("email").trim().toLowerCase(),
          universityId: formData.get("universityId").trim(),
          password: formData.get("password"),
        }),
      });
      setState(payload);
      state.currentPage = "home";
      render();
      showToast("Account created successfully.");
    } catch (error) {
      showToast(error.message);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    try {
      const payload = await api("/api/login", {
        method: "POST",
        body: JSON.stringify({
          email: formData.get("email").trim().toLowerCase(),
          password: formData.get("password"),
        }),
      });
      setState(payload);
      state.currentPage = "home";
      render();
      showToast("Logged in successfully.");
    } catch (error) {
      showToast(error.message);
    }
  });
}

function renderDashboard() {
  document.body.classList.remove("guest-mode");
  const user = state.currentUser;
  app.innerHTML = document.querySelector("#dashboard-template").innerHTML;
  document.querySelector("#welcome-title").textContent = user.name;
  document.querySelector("#welcome-subtitle").textContent = `${user.universityId} | ${user.email}`;
  document.querySelector("#admin-nav-btn").classList.toggle("hidden", !isAdmin(user));
  document.querySelector("#report-lost-nav-btn").classList.toggle("hidden", isAdmin(user));
  document.querySelector("#report-found-nav-btn").classList.toggle("hidden", isAdmin(user));
  renderStats(user);
  document.querySelector("#page-content").innerHTML = renderPageContent(user);
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.classList.toggle("active", button.getAttribute("data-nav") === state.currentPage);
  });
  bindDashboardEvents(user);
}

function bindDashboardEvents(user) {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentPage = button.getAttribute("data-nav");
      render();
    });
  });

  document.querySelector("#logout-btn").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST", body: "{}" }).catch(() => {});
    state.currentUser = null;
    state.currentPage = "home";
    render();
  });

  document.querySelector("#seed-data-btn").addEventListener("click", async () => {
    try {
      const payload = await api("/api/demo", { method: "POST", body: "{}" });
      setState(payload);
      render();
      showToast("Demo data loaded.");
    } catch (error) {
      showToast(error.message);
    }
  });

  const lostForm = document.querySelector("#lost-item-form");
  if (lostForm) {
    lostForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      try {
        const payload = await api("/api/lost-items", {
          method: "POST",
          body: JSON.stringify({
            itemName: formData.get("itemName").trim(),
            description: formData.get("description").trim(),
            location: formData.get("location").trim(),
            dateTime: formData.get("dateTime"),
            imageData: await fileToDataUrl(formData.get("image")),
          }),
        });
        setState(payload);
        state.currentPage = "your-lost";
        render();
        showToast("Lost item submitted.");
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  const foundForm = document.querySelector("#found-item-form");
  if (foundForm) {
    foundForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(event.currentTarget);
      try {
        const payload = await api("/api/found-items", {
          method: "POST",
          body: JSON.stringify({
            itemName: formData.get("itemName").trim(),
            description: formData.get("description").trim(),
            location: formData.get("location").trim(),
            dateTime: formData.get("dateTime"),
            imageData: await fileToDataUrl(formData.get("image")),
          }),
        });
        setState(payload);
        state.currentPage = "your-discoveries";
        render();
        showToast("Found item submitted.");
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  document.querySelectorAll("[data-claim-btn]").forEach((button) => {
    button.addEventListener("click", async () => {
      const foundItemId = button.getAttribute("data-claim-btn");
      const proof = document.querySelector(`[data-proof-for="${foundItemId}"]`).value.trim();
      if (proof.length < 12) {
        showToast("Add more identifying proof before claiming.");
        return;
      }
      try {
        const payload = await api("/api/claims", {
          method: "POST",
          body: JSON.stringify({ foundItemId, proof }),
        });
        setState(payload);
        state.currentPage = "claims";
        render();
        showToast("Claim submitted for verification.");
      } catch (error) {
        showToast(error.message);
      }
    });
  });

  document.querySelectorAll("[data-delete-item]").forEach((button) => {
    button.addEventListener("click", async () => {
      const [itemType, itemId] = button.getAttribute("data-delete-item").split(":");
      const confirmed = window.confirm(`Delete this ${itemType} item report?`);
      if (!confirmed) return;
      try {
        const payload = await api(`/api/items/${itemType}/${itemId}/delete`, { method: "POST", body: "{}" });
        setState(payload);
        render();
        showToast(`${itemType === "lost" ? "Lost" : "Found"} item deleted.`);
      } catch (error) {
        showToast(error.message);
      }
    });
  });

  document.querySelectorAll("[data-approve-claim]").forEach((button) => {
    button.addEventListener("click", () => handleClaimAction(button.getAttribute("data-approve-claim"), "approve", "Claim approved."));
  });
  document.querySelectorAll("[data-reject-claim]").forEach((button) => {
    button.addEventListener("click", () => handleClaimAction(button.getAttribute("data-reject-claim"), "reject", "Claim rejected."));
  });
  document.querySelectorAll("[data-dropoff-claim]").forEach((button) => {
    button.addEventListener("click", () => handleClaimAction(button.getAttribute("data-dropoff-claim"), "dropoff", "Marked as dropped at office."));
  });
  document.querySelectorAll("[data-collected-claim]").forEach((button) => {
    button.addEventListener("click", () => handleClaimAction(button.getAttribute("data-collected-claim"), "collect", "Pickup marked as completed."));
  });
}

async function handleClaimAction(claimId, action, successMessage) {
  try {
    const payload = await api(`/api/claims/${claimId}/${action}`, { method: "POST", body: "{}" });
    setState(payload);
    state.currentPage = action === "approve" || action === "reject" ? "admin" : "claims";
    render();
    showToast(successMessage);
  } catch (error) {
    showToast(error.message);
  }
}

function render() {
  if (state.currentUser) {
    renderDashboard();
  } else {
    renderGuestView();
  }
}

refreshState();
