// dashboard.js

function switchTab(name) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.id === `tab-${name}`));
}

function showLoading(areaId, text) {
    document.getElementById(areaId).innerHTML = `<p class="result-msg loading">${text}</p>`;
}

function showError(areaId, message) {
    document.getElementById(areaId).innerHTML = `<div class="result-msg error"><i class="fas fa-triangle-exclamation"></i> ${message}</div>`;
}

// ===== CONCEAL =====
async function doConceal() {
    const fileInput = document.getElementById("concealImage");
    const message = document.getElementById("concealMessage").value.trim();
    const password = document.getElementById("concealPassword").value;

    if (!fileInput.files.length) return showError("concealResult", "Choose a cover image first.");
    if (!message || !password) return showError("concealResult", "Both a message and a password are required.");

    showLoading("concealResult", "Encrypting and hiding your message...");

    const form = new FormData();
    form.append("image", fileInput.files[0]);
    form.append("message", message);
    form.append("password", password);

    const res = await fetch("/api/conceal", { method: "POST", body: form });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Something went wrong." }));
        return showError("concealResult", err.error);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    document.getElementById("concealResult").innerHTML = `
        <div class="result-msg success">
            <i class="fas fa-circle-check"></i> Message hidden successfully. The image looks completely unchanged to the eye.
        </div>
        <a class="download-link" href="${url}" download="concealed.png">
            <i class="fas fa-download"></i> Download concealed.png
        </a>
    `;
}

// ===== DETECT =====
async function doDetect() {
    const fileInput = document.getElementById("detectImage");
    if (!fileInput.files.length) return showError("detectResult", "Choose an image to scan first.");

    showLoading("detectResult", "Running signature check and statistical analysis...");

    const form = new FormData();
    form.append("image", fileInput.files[0]);

    const res = await fetch("/api/detect", { method: "POST", body: form });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Something went wrong." }));
        return showError("detectResult", err.error);
    }

    const result = await res.json();

    let cardClass = "clean";
    if (result.signature_detected) cardClass = "confirmed";
    else if (result.chi_square_score >= 70) cardClass = "suspicious";
    else if (result.chi_square_score >= 40) cardClass = "uncertain";

    document.getElementById("detectResult").innerHTML = `
        <div class="verdict-card ${cardClass}">
            <div class="verdict-title">${result.verdict}</div>
            <div class="verdict-detail">
                Signature check is exact and only catches this tool's own output. The chi-square score is a statistical
                heuristic that can flag LSB tampering from other tools too, but it's a probability, not a certainty.
            </div>
            <div class="score-row">
                <div class="score-box">
                    <span class="score-val">${result.signature_detected ? "YES" : "NO"}</span>
                    <span class="score-label">Signature Match</span>
                </div>
                <div class="score-box">
                    <span class="score-val">${result.chi_square_score}</span>
                    <span class="score-label">Chi-Square Score</span>
                </div>
            </div>
        </div>
        <div class="lsb-reveal">
            <h4><i class="fas fa-layer-group"></i> Extracted Bit-Plane</h4>
            <img src="data:image/png;base64,${result.lsb_plane}" alt="LSB plane" />
            <p class="lsb-note">This is just the last bit of every pixel, isolated and rendered as its own image. It's a real forensic technique, though on its own it usually just looks like noise either way, that's exactly why the statistics above matter more than eyeballing it.</p>
        </div>
    `;
}

// ===== REVEAL =====
async function doReveal() {
    const fileInput = document.getElementById("revealImage");
    const password = document.getElementById("revealPassword").value;

    if (!fileInput.files.length) return showError("revealResult", "Choose a stego image first.");
    if (!password) return showError("revealResult", "Enter the password used to encrypt it.");

    showLoading("revealResult", "Extracting and decrypting...");

    const form = new FormData();
    form.append("image", fileInput.files[0]);
    form.append("password", password);

    const res = await fetch("/api/reveal", { method: "POST", body: form });
    const result = await res.json();

    if (!res.ok) {
        return showError("revealResult", result.error);
    }

    document.getElementById("revealResult").innerHTML = `
        <div class="result-msg success">
            <i class="fas fa-unlock"></i> Message recovered:
            <div style="margin-top:10px; padding:12px; background:rgba(10,6,6,0.5); border-radius:6px; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; white-space:pre-wrap;">${result.message}</div>
        </div>
    `;
}
