/**
 * SpendWise – script.js
 * Handles:
 *  1. Mobile sidebar toggle
 *  2. Auto-dismiss flash messages
 *  3. Delete confirmation dialog
 *  4. Donut chart on dashboard (vanilla Canvas API)
 *  5. Micro-animations & interaction enhancements
 */

"use strict";

// ─── 1. Mobile Sidebar ───────────────────────────────────────────
const hamburger      = document.getElementById("hamburger");
const sidebar        = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

function openSidebar() {
  sidebar.classList.add("open");
  sidebarOverlay.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeSidebar() {
  sidebar.classList.remove("open");
  sidebarOverlay.classList.remove("active");
  document.body.style.overflow = "";
}

if (hamburger)      hamburger.addEventListener("click", openSidebar);
if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebar);

// Close sidebar when a nav link is clicked on mobile
document.querySelectorAll(".nav-link").forEach(function (link) {
  link.addEventListener("click", function () {
    if (window.innerWidth < 768) closeSidebar();
  });
});

// ─── Theme Toggle ────────────────────────────────────────────────
(function initTheme() {
  var html        = document.documentElement;
  var btn         = document.getElementById("themeToggle");
  var iconEl      = document.getElementById("themeIcon");
  var labelEl     = document.getElementById("themeLabel");

  // Sync UI to current theme state
  function syncUI() {
    var isDark = html.getAttribute("data-theme") === "dark";
    if (iconEl)  iconEl.textContent  = isDark ? "🌙" : "☀️";
    if (labelEl) labelEl.textContent = isDark ? "Dark mode" : "Light mode";
  }

  // Apply on load (theme already set by anti-flash script in <head>)
  syncUI();

  if (btn) {
    btn.addEventListener("click", function () {
      var isDark = html.getAttribute("data-theme") === "dark";
      if (isDark) {
        html.removeAttribute("data-theme");
        try { localStorage.setItem("sw-theme", "light"); } catch(e) {}
      } else {
        html.setAttribute("data-theme", "dark");
        try { localStorage.setItem("sw-theme", "dark"); } catch(e) {}
      }
      syncUI();
      // Re-draw chart so donut hole colour updates
      if (typeof redrawChart === "function") redrawChart();
    });
  }
}());

// ─── 2. Auto-dismiss flash messages after 5 s ────────────────────
document.querySelectorAll(".flash").forEach(function (el) {
  setTimeout(function () {
    el.style.transition = "opacity 0.4s ease, transform 0.4s ease";
    el.style.opacity    = "0";
    el.style.transform  = "translateY(-4px)";
    setTimeout(function () { el.remove(); }, 420);
  }, 5000);
});

// ─── 3. Delete confirmation ──────────────────────────────────────
function confirmDelete(title) {
  return window.confirm(
    'Delete "' + title + '"?\n\nThis action cannot be undone.'
  );
}

// ─── 4. Stat cards count-up animation ───────────────────────────
(function animateStats() {
  var statValues = document.querySelectorAll(".stat-value, .card-value");
  statValues.forEach(function (el) {
    var text = el.textContent.trim();
    // Only animate INR values
    if (!text.startsWith("₹")) return;
    var numStr = text.replace(/[₹,]/g, "");
    var target = parseFloat(numStr);
    if (isNaN(target) || target === 0) return;

    var start    = 0;
    var duration = 900;
    var startTime = null;

    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var current  = start + (target - start) * easeOut(progress);

      // Re-format with ₹ and decimal
      var formatted = "₹" + current.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
      el.textContent = formatted;

      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = text; // Restore exact original
    }
    requestAnimationFrame(step);
  });
}());

// ─── 5. Progress bar animated fill ──────────────────────────────
(function animateProgressBars() {
  var bars = document.querySelectorAll(".progress-bar");
  bars.forEach(function (bar) {
    var target = bar.style.width;
    bar.style.width = "0";
    // Trigger reflow, then animate
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bar.style.width = target;
      });
    });
  });
}());

// ─── 6. Stagger txn-item / table-row entrance ───────────────────
(function staggerItems() {
  var items = document.querySelectorAll(".txn-item, .table-row");
  items.forEach(function (item, i) {
    item.style.opacity   = "0";
    item.style.transform = "translateY(8px)";
    item.style.transition = "opacity 0.25s ease " + (i * 40) + "ms, transform 0.25s ease " + (i * 40) + "ms";
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        item.style.opacity   = "1";
        item.style.transform = "translateY(0)";
      });
    });
  });
}());

// ─── 7. Donut chart (dashboard) ──────────────────────────────────
var redrawChart = null; // exposed for theme toggle

(function drawCategoryChart() {
  var canvas = document.getElementById("categoryChart");
  if (!canvas) return;

  var labelsEl  = document.getElementById("categoryData");
  var amountsEl = document.getElementById("categoryAmounts");
  if (!labelsEl || !amountsEl) return;

  var labels  = JSON.parse(labelsEl.textContent);
  var amounts = JSON.parse(amountsEl.textContent);

  if (!labels.length) return;

  var COLORS = [
    "#6366f1", "#f59e0b", "#10b981", "#ef4444",
    "#3b82f6", "#a855f7", "#f97316", "#ec4899", "#14b8a6"
  ];

  var total = amounts.reduce(function (s, v) { return s + v; }, 0);
  if (total === 0) return;

  var dpr  = window.devicePixelRatio || 1;
  var size = 200;
  canvas.width  = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width  = size + "px";
  canvas.style.height = size + "px";

  var ctx    = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  var cx     = size / 2;
  var cy     = size / 2;
  var outerR = size / 2 - 10;
  var innerR = outerR * 0.56;
  var gap    = 0.018;

  // Read chart hole colour from CSS custom property
  function getHoleColor() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--chart-hole").trim() || "#FFFFFF";
  }

  function draw(animated) {
    var animDuration = animated ? 750 : 0;
    var animStart    = null;

    function frame(timestamp) {
      if (!animStart) animStart = timestamp;
      var progress = animDuration > 0
        ? Math.min((timestamp - animStart) / animDuration, 1)
        : 1;
      var eased = progress < 0.5
        ? 2 * progress * progress
        : -1 + (4 - 2 * progress) * progress;

      ctx.clearRect(0, 0, size, size);

      var runningStart = -Math.PI / 2;
      amounts.forEach(function (val, i) {
        var slice = (val / total) * 2 * Math.PI * eased;
        var end   = runningStart + slice - (eased > 0.01 ? gap : 0);

        ctx.beginPath();
        ctx.arc(cx, cy, outerR, runningStart + gap / 2, end);
        ctx.arc(cx, cy, innerR, end, runningStart + gap / 2, true);
        ctx.closePath();
        ctx.fillStyle = COLORS[i % COLORS.length];
        ctx.fill();

        runningStart += slice;
      });

      // Donut hole
      ctx.beginPath();
      ctx.arc(cx, cy, innerR - 1, 0, 2 * Math.PI);
      ctx.fillStyle = getHoleColor();
      ctx.fill();

      // Centre label
      if (eased > 0.8) {
        var opacity = Math.min((eased - 0.8) / 0.2, 1);
        ctx.globalAlpha = opacity;
        var inrTotal = (total / 100).toFixed(0);
        var isDark   = document.documentElement.getAttribute("data-theme") === "dark";
        ctx.fillStyle = isDark ? "#666666" : "#A3A3A3";
        ctx.font      = "500 11px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Total", cx, cy - 11);
        ctx.fillStyle = isDark ? "#F5F5F5" : "#171717";
        ctx.font      = "600 15px Inter, sans-serif";
        ctx.fillText("₹" + Number(inrTotal).toLocaleString("en-IN"), cx, cy + 10);
        ctx.globalAlpha = 1;
      }

      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // Initial animated draw
  draw(true);

  // Expose redraw (no animation) for theme toggle
  redrawChart = function () { draw(false); };

  // Sync legend dot colours
  var legendDots = document.querySelectorAll(".legend-dot");
  legendDots.forEach(function (dot, i) {
    dot.style.background = COLORS[i % COLORS.length];
  });
}());

// ─── 8. Trend bar chart (dashboard) ────────────────────────────────
var redrawTrend = null; // exposed for theme toggle

(function drawTrendChart() {
  var canvas = document.getElementById("trendChart");
  if (!canvas) return;

  var labelsEl  = document.getElementById("trendLabels");
  var totalsEl  = document.getElementById("trendTotals");
  if (!labelsEl || !totalsEl) return;

  var labels = JSON.parse(labelsEl.textContent);
  var totals = JSON.parse(totalsEl.textContent); // paise
  if (!labels.length) return;

  var dpr = window.devicePixelRatio || 1;
  var W = 560, H = 180;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = "100%";
  canvas.style.maxWidth = W + "px";
  canvas.style.height = H + "px";

  var ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  function themeColors() {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      bar:      isDark ? "#818cf8" : "#6366f1",
      barDim:   isDark ? "#3a3f7a" : "#c7d2fe",
      text:     isDark ? "#A3A3A3" : "#737373",
      grid:     isDark ? "#272727" : "#E5E5E5",
      valueTxt: isDark ? "#F5F5F5" : "#171717"
    };
  }

  function draw() {
    var C = themeColors();
    ctx.clearRect(0, 0, W, H);

    var max = Math.max.apply(null, totals.concat([1]));
    var padL = 8, padR = 8, padT = 26, padB = 26;
    var plotW = W - padL - padR;
    var plotH = H - padT - padB;
    var n = labels.length;
    var slot = plotW / n;
    var barW = Math.min(slot * 0.55, 56);

    // Baseline
    ctx.strokeStyle = C.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, H - padB);
    ctx.lineTo(W - padR, H - padB);
    ctx.stroke();

    totals.forEach(function (val, i) {
      var x = padL + slot * i + (slot - barW) / 2;
      var h = max > 0 ? (val / max) * plotH : 0;
      var y = H - padB - h;
      var isCurrent = (i === n - 1);

      // Rounded bar
      ctx.fillStyle = isCurrent ? C.bar : C.barDim;
      var r = Math.min(5, barW / 2);
      ctx.beginPath();
      if (h > 0) {
        ctx.moveTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.lineTo(x + barW - r, y);
        ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
        ctx.lineTo(x + barW, H - padB);
        ctx.lineTo(x, H - padB);
        ctx.closePath();
        ctx.fill();
      }

      // Value label
      ctx.fillStyle = C.valueTxt;
      ctx.font = "600 10px Inter, sans-serif";
      ctx.textAlign = "center";
      var inr = "₹" + Math.round(val / 100).toLocaleString("en-IN");
      ctx.fillText(inr, x + barW / 2, Math.max(y - 6, 10));

      // Month label
      ctx.fillStyle = C.text;
      ctx.font = "500 11px Inter, sans-serif";
      ctx.fillText(labels[i], x + barW / 2, H - padB + 16);
    });
  }

  draw();
  redrawTrend = draw;

  // Redraw with the donut chart on theme change
  var origRedraw = redrawChart;
  redrawChart = function () {
    if (typeof origRedraw === "function") origRedraw();
    draw();
  };
}());
