// Validate tổng % realtime — cùng ngưỡng với backend (0.01%)
(function () {
  const inputs = document.querySelectorAll(".pigment-input");
  const totalEl = document.getElementById("totalPct");
  const statusEl = document.getElementById("totalStatus");
  const submitBtn = document.getElementById("submitBtn");

  function update() {
    let total = 0, hasAny = false;
    inputs.forEach(i => {
      const v = parseFloat((i.value || "").replace(",", "."));
      if (!isNaN(v) && v > 0) { total += v; hasAny = true; }
    });
    totalEl.textContent = (Math.round(total * 1000) / 1000) + "%";
    statusEl.className = "badge";
    if (!hasAny) {
      statusEl.textContent = "CHƯA KHAI BÁO";
      statusEl.classList.add("badge-muted");
      submitBtn.disabled = true;
    } else if (Math.abs(total - 100) < 0.01) {
      statusEl.textContent = "ĐẠT";
      statusEl.classList.add("badge-ok");
      submitBtn.disabled = false;
    } else {
      statusEl.textContent = "SAI TỔNG";
      statusEl.classList.add("badge-warn");
      submitBtn.disabled = true;
    }
  }

  inputs.forEach(i => i.addEventListener("input", update));
  update();
})();

// Đồng bộ color picker <-> ô HEX
(function () {
  const picker = document.getElementById("hexPicker");
  const text = document.getElementById("hexText");
  if (!picker || !text) return;
  picker.addEventListener("input", () => { text.value = picker.value.toUpperCase(); });
  text.addEventListener("input", () => {
    if (/^#[0-9A-Fa-f]{6}$/.test(text.value.trim())) picker.value = text.value.trim();
  });
})();
