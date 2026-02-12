// A named, globally callable function
function showDoDConsentBanner() {
  const STORAGE_KEY = "dod_notice_consent_accepted_v1";

  // If already accepted this session, do nothing
  if (sessionStorage.getItem(STORAGE_KEY) === "1") {
    return;
  }

  const banner = document.getElementById("dod-banner");
  const btnAccept = document.getElementById("dod-accept");
  const btnDecline = document.getElementById("dod-decline");

  if (!banner || !btnAccept) {
    console.error("DoD Banner: Required HTML elements not found.");
    return;
  }

  banner.hidden = false;

  btnAccept.onclick = function () {
    sessionStorage.setItem(STORAGE_KEY, "1");
    banner.hidden = true;
  };

  if (btnDecline) {
    btnDecline.onclick = function () {
      window.location.href = "../";
    };
  }
}