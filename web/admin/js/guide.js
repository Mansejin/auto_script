(function () {
  const toc = document.getElementById("guideToc");
  if (!toc) return;

  const links = [...toc.querySelectorAll('a[href^="#"]')];
  const sections = links
    .map((link) => {
      const id = link.getAttribute("href").slice(1);
      const el = document.getElementById(id);
      return el ? { link, el } : null;
    })
    .filter(Boolean);

  function setActive(id) {
    links.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
    });
  }

  if ("IntersectionObserver" in window && sections.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: [0, 0.25, 0.5, 1] }
    );
    sections.forEach(({ el }) => observer.observe(el));
  }

  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      const id = link.getAttribute("href").slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      setActive(id);
      history.replaceState(null, "", `#${id}`);
    });
  });

  const hash = window.location.hash.slice(1);
  if (hash && document.getElementById(hash)) {
    setActive(hash);
  }
})();

(function () {
  const STYLE_GUIDE_SAMPLE = [
    "【문체】",
    "- 서술체(합니다체) 사용. 구어체·감탄사·이모지 금지",
    "- 학생 실명 대신 「학생」 또는 성 없이 이름만 표기",
    "",
    "【행발】",
    "- 태도·성품·대인관계·책임감 중심 서술",
    "- 활동 나열보다 관찰된 변화·성장 강조",
    "- 목표 분량: 600~850바이트 (NEIS 900바이트 이내)",
    "",
    "【세특】",
    "- 수업·탐구·발표 활동과 태도를 연결",
    "- 과목별 3~5문장, 문단당 3~4문장",
    "- 목표 분량: 1000~1400바이트",
    "",
    "【공통】",
    "- 부정적 표현 완화, 판단보다 사실·관찰 위주",
    "- 동일 표현 반복 지양",
  ].join("\n");

  const field = document.getElementById("guideStyleTypewriter");
  const demo = document.getElementById("guideStyleDemo");
  if (!field || !demo) return;

  let started = false;
  let timer = 0;

  function typeNext(index) {
    if (index >= STYLE_GUIDE_SAMPLE.length) {
      field.classList.remove("is-typing");
      return;
    }
    field.value += STYLE_GUIDE_SAMPLE[index];
    field.scrollTop = field.scrollHeight;
    const delay = STYLE_GUIDE_SAMPLE[index] === "\n" ? 28 : 14;
    timer = window.setTimeout(() => typeNext(index + 1), delay);
  }

  function startTypewriter() {
    if (started) return;
    started = true;
    window.clearTimeout(timer);
    field.value = "";
    field.classList.add("is-typing");
    typeNext(0);
  }

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          startTypewriter();
          observer.disconnect();
        }
      },
      { threshold: 0.25 }
    );
    observer.observe(demo);
  } else {
    startTypewriter();
  }
})();
