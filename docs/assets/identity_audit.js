/* Source-linked, privacy-minimal stakeholder labeling audit. */
(async function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const status = $("identity-audit-status");
  if (!status) return;
  const n = v => Number(v || 0).toLocaleString();
  const label = {
    cross_sector_conflict: "Different sectors",
    school_institution_vs_staff: "School institution vs staff",
    model_specific_deterministic_unknown: "LLM has a specific role; rules abstain",
    deterministic_specific_model_unknown: "Rules have a specific role; LLM abstains",
    unmapped_taxonomy: "Old LLM lacks this category",
    both_unknown: "Both unresolved",
    same_specific_label: "Both assign the same role",
  };
  let all = [], visible = [];
  try {
    const response = await fetch("./data/stakeholder_label_audit.json", {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const report = await response.json();
    const c = report.summary.comparison_counts, d = report.coverage;
    const both = d.both_specific_comparable;
    const cross = c.cross_sector_conflict || 0;
    const raw = report.summary.raw_disagreements_among_comparable || 0;
    const comparable = report.summary.raw_disagreement_denominator || 0;
    const items = [
      [n(raw) + " / " + n(comparable), "Different labels, including abstentions"],
      [n(cross) + " / " + n(both), "Cross-sector conflicts when both assign roles"],
      [n(d.second_pass_completed) + " / " + n(d.filings_with_old_llm_labels), "Dedicated identity model records completed"],
      [n(report.summary.human_adjudicated), "Source-adjudicated deterministic identities"],
    ];
    $("identity-audit-metrics").replaceChildren();
    for (const [value, caption] of items) {
      const box = document.createElement("div");
      box.className = "ps-stat";
      const strong = document.createElement("strong");
      strong.textContent = value;
      const small = document.createElement("span");
      small.textContent = caption;
      box.append(strong, small);
      $("identity-audit-metrics").append(box);
    }
    all = report.filings || [];
    status.textContent = "Compared " + n(all.length) + " filing records. These are automated disagreements, not measured errors. Source citations are FCC filing links.";
    if (d.second_pass_completed === 0) {
      $("identity-audit-model-note").textContent =
        "The dedicated identity-only model pass has been queued; no second-pass results have been published yet. The audit below compares the older argument-extraction model with source-based rules.";
    } else {
      $("identity-audit-model-note").textContent =
        "Dedicated identity-only candidates are available for " + n(d.second_pass_completed) +
        " filings. They remain machine suggestions, not automatically corrected labels.";
    }
    function render() {
      const filter = $("identity-audit-filter").value;
      const search = $("identity-audit-query").value.trim().toLowerCase();
      visible = all.filter(r => (!filter || r.comparison === filter ||
        (filter === "second_pass_conflict" && r.second_pass_conflict)) &&
        (!search || [r.id, r.organization, r.deterministic_role, r.old_llm_role, r.industry_focus]
          .some(s => String(s || "").toLowerCase().includes(search))));
      $("identity-audit-count").textContent = n(visible.length) + " matching filings, showing up to 120 highest-priority cases.";
      const root = $("identity-audit-rows");
      root.replaceChildren();
      for (const r of visible.slice(0,120)) {
        const tr = document.createElement("tr");
        const link = document.createElement("a");
        link.href = r.source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = r.organization || ("FCC filing " + r.id);
        const name = document.createElement("td");
        name.append(link);
        const review = document.createElement("a");
        review.href = "./players.html?review=" + encodeURIComponent(r.id) + "#ps-review-panel";
        review.textContent = "Review identity";
        review.style.marginLeft = "0.6rem";
        name.append(review);
        if (r.organization) {
          const code = document.createElement("small");
          code.textContent = " · " + r.id;
          name.append(code);
        }
        const det = document.createElement("td");
        det.textContent = r.deterministic_role.replaceAll("_", " ");
        const llm = document.createElement("td");
        llm.textContent = r.old_llm_role.replaceAll("_", " ");
        const flag = document.createElement("td");
        flag.textContent = label[r.comparison] || r.comparison;
        if (r.second_pass) {
          flag.textContent += " · New identity model: " + r.second_pass.role.replaceAll("_", " ");
        }
        tr.append(name,det,llm,flag);
        root.append(tr);
      }
    }
    $("identity-audit-filter").addEventListener("change",render);
    $("identity-audit-query").addEventListener("input",render);
    $("identity-audit-filter").value = "cross_sector_conflict";
    render();
  } catch (error) {
    status.textContent = "Identity audit not published yet. The build workflow will populate this section after validation. " + error.message;
  }
})();
