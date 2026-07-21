// Preview phiếu cân realtime — cùng công thức với services/calculator.py
(function () {
  const form = document.getElementById("weighingForm");
  const ratios = JSON.parse(form.dataset.ratios || "[]");
  const names = JSON.parse(form.dataset.names || "[]");
  const tongTP = document.getElementById("tongTP");
  const tyLe = document.getElementById("tyLePigment");
  const tbody = document.querySelector("#previewTable tbody");

  const fmt = v => v.toLocaleString("vi-VN", { maximumFractionDigits: 1 });

  function update() {
    const tong = parseFloat((tongTP.value || "0").replace(",", "."));
    const tl = parseFloat((tyLe.value || "0").replace(",", ".")) / 100;
    tbody.innerHTML = "";
    if (!(tong > 0) || !(tl > 0 && tl < 1)) return;

    const tongPigment = tong * tl;
    const tongCT = ratios.reduce((a, b) => a + b, 0);
    const rows = [["BASE THÀNH PHẦN A", tong * (1 - tl)]];
    ratios.forEach((r, i) => {
      if (r > 0 && tongCT > 0) rows.push([names[i], tongPigment * (r / tongCT)]);
    });
    let sum = 0;
    rows.forEach(([ten, kl]) => {
      sum += kl;
      tbody.insertAdjacentHTML("beforeend",
        `<tr><td>${ten}</td><td class="num"><b>${fmt(kl)}</b></td></tr>`);
    });
    tbody.insertAdjacentHTML("beforeend",
      `<tr class="total-row"><td><b>TỔNG</b></td><td class="num"><b>${fmt(sum)}</b></td></tr>`);
  }

  [tongTP, tyLe].forEach(el => el.addEventListener("input", update));
  update();
})();
