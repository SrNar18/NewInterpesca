// ===== BACK TO TOP =====
const backTop = document.getElementById('backTop');
window.addEventListener('scroll', () => {
  backTop.classList.toggle('visible', window.scrollY > 400);
});
backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

// ===== HAMBURGER MENU =====
const hamburger = document.getElementById('hamburger');
const nav = document.getElementById('nav');
hamburger.addEventListener('click', () => nav.classList.toggle('open'));
nav.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => nav.classList.remove('open'));
});

// ===== ANIMATED COUNTERS =====
function animateCounter(el) {
  const target = parseInt(el.dataset.target);
  const duration = 1500;
  const step = target / (duration / 16);
  let current = 0;
  el.textContent = '0'; // reinicia visualment abans d'animar
  const timer = setInterval(() => {
    current += step;
    if (current >= target) { current = target; clearInterval(timer); }
    el.textContent = Math.floor(current);
  }, 16);
}

const statsSection = document.querySelector('.stats');
const statsObserver = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting) {
    statsSection.classList.add('visible');
    document.querySelectorAll('.stat__number').forEach(animateCounter);
    statsObserver.disconnect();
  }
}, { threshold: 0.35 });
statsObserver.observe(statsSection);

// ===== SCROLL REVEAL =====
const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => revealObserver.observe(el));

// ===== FAQ ACCORDION =====
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.parentElement;
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
    if (!isOpen) item.classList.add('open');
  });
});

// ===== CONTACT FORM =====
const contactForm = document.getElementById('contactForm');
const toast = document.getElementById('toast');

// ── Regles de validació ──
const RULES = {
  'f-nom': {
    required: true,
    minLen: 2,
    pattern: /^[\p{L}\s'\-\.]{2,80}$/u,
    msgs: {
      required: 'El nom és obligatori.',
      pattern:  'Introdueix un nom vàlid (mínim 2 caràcters, sense números).',
    }
  },
  'f-telefon': {
    required: true,
    // Accepta formats: +376 123456, 123 456 789, (376) 123456, etc.
    pattern: /^\+?[\d\s\-\(\)]{7,20}$/,
    msgs: {
      required: 'El telèfon és obligatori.',
      pattern:  'Introdueix un número de telèfon vàlid (ex: +376 123456).',
    }
  },
  'f-email': {
    required: false,
    // RFC 5322 simplificat
    pattern: /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~\-]+@[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)+$/,
    msgs: {
      pattern: 'Introdueix una adreça de correu vàlida (ex: nom@empresa.com).',
    }
  },
  'f-tipus': {
    required: true,
    msgs: {
      required: 'Selecciona el tipus de negoci.',
    }
  },
};

// ── Helpers d'error ──
function getErrSpan(field) {
  // El span sempre viu dins el .field-wrap pare del camp
  const wrap = field.closest('.field-wrap');
  let span = wrap.querySelector('.field-error-msg');
  if (!span) {
    span = document.createElement('span');
    span.className = 'field-error-msg';
    span.setAttribute('role', 'alert');
    span.setAttribute('aria-live', 'polite');
    wrap.appendChild(span);
  }
  return span;
}

function setError(field, msg) {
  field.classList.add('input-error');
  field.classList.remove('input-ok');
  field.setAttribute('aria-invalid', 'true');
  const span = getErrSpan(field);
  span.textContent = msg;
  span.classList.add('visible');
}

function clearError(field) {
  field.classList.remove('input-error');
  field.setAttribute('aria-invalid', 'false');
  const span = getErrSpan(field);
  span.classList.remove('visible');
}

function setOk(field) {
  clearError(field);
  field.classList.add('input-ok');
}

// ── Valida un camp individual ──
function validateField(field) {
  const id = field.id;
  const rule = RULES[id];
  if (!rule) return true;

  const val = field.value.trim();

  if (rule.required && !val) {
    setError(field, rule.msgs.required);
    return false;
  }
  if (val && rule.pattern && !rule.pattern.test(val)) {
    setError(field, rule.msgs.pattern);
    return false;
  }
  setOk(field);
  return true;
}

// ── Valida el formulari complet ──
function validateForm() {
  let valid = true;

  Object.keys(RULES).forEach(id => {
    const field = contactForm.querySelector('#' + id);
    if (field && !validateField(field)) valid = false;
  });

  // Checkbox 1 — Protecció de dades
  const privacy = contactForm.querySelector('#f-privacy');
  const privacyLabel = contactForm.querySelector('label[for="f-privacy"]');
  const privacyErrSpan = document.getElementById('privacy-error');
  if (!privacy.checked) {
    privacyLabel.classList.add('input-error');
    privacyErrSpan.textContent = 'Has d\'acceptar la Protecció de Dades.';
    privacyErrSpan.classList.add('visible');
    valid = false;
  } else {
    privacyLabel.classList.remove('input-error');
    privacyErrSpan.classList.remove('visible');
  }

  // Checkbox 2 — Consentiment d'emmagatzematge RGPD
  const consent = contactForm.querySelector('#f-consent');
  const consentLabel = contactForm.querySelector('label[for="f-consent"]');
  const consentErrSpan = document.getElementById('consent-error');
  if (!consent.checked) {
    consentLabel.classList.add('input-error');
    consentErrSpan.textContent = 'Has de donar el consentiment per continuar.';
    consentErrSpan.classList.add('visible');
    valid = false;
  } else {
    consentLabel.classList.remove('input-error');
    consentErrSpan.classList.remove('visible');
  }

  return valid;
}

// ── Feedback en temps real (blur) ──
Object.keys(RULES).forEach(id => {
  const field = contactForm.querySelector('#' + id);
  if (!field) return;
  field.addEventListener('blur', () => validateField(field));
  field.addEventListener('input', () => {
    if (field.classList.contains('input-error')) validateField(field);
  });
});

// ── Submit ──
contactForm.addEventListener('submit', async e => {
  e.preventDefault();

  if (!validateForm()) {
    // Fa scroll al primer camp amb error
    const firstError = contactForm.querySelector('.input-error');
    if (firstError) firstError.focus();
    return;
  }

  const submitBtn = contactForm.querySelector('[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Enviant...';
  submitBtn.disabled = true;

  const data = {
    nom:      contactForm.querySelector('#f-nom').value.trim(),
    empresa:  contactForm.querySelector('#f-empresa').value.trim(),
    telefon:  contactForm.querySelector('#f-telefon').value.trim(),
    email:    contactForm.querySelector('#f-email').value.trim(),
    tipus:    contactForm.querySelector('#f-tipus').value,
    missatge: contactForm.querySelector('#f-missatge').value.trim(),
    _subject: 'Nova consulta des de la web Interpesca',
    _template: 'table',
  };

  // URL del Google Apps Script (substitueix per la teva URL de desplegament)
  const SHEETS_WEBHOOK = 'https://script.google.com/macros/s/AKfycbyRtuGnGmynw8TolWcXCuEAHRUk2vyaitzJuyg8g4LAnm1uwhugMdSIXAWyHsQu5EvB/exec';

  try {
    // Envia en paral·lel: correu (FormSubmit) + registre (Google Sheets)
    const [res] = await Promise.allSettled([
      fetch('https://formsubmit.co/ajax/adrianlima8107@gmail.com', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(data),
      }),
      SHEETS_WEBHOOK !== 'ENGANXA_AQUÍ_LA_URL_DEL_APPS_SCRIPT'
        ? fetch(SHEETS_WEBHOOK + '?' + new URLSearchParams({
            nom:      data.nom,
            empresa:  data.empresa,
            telefon:  data.telefon,
            email:    data.email,
            tipus:    data.tipus,
            missatge: data.missatge,
          }).toString(), { method: 'GET', mode: 'no-cors' })
            .catch(() => {})
        : Promise.resolve(),
    ]);

    const emailOk = res.status === 'fulfilled' && res.value?.ok;

    if (emailOk) {
      toast.textContent = 'Gràcies pel teu missatge. Ens posarem en contacte amb tu en el menor temps possible. Si necessites resposta urgent, escriu-nos directament per WhatsApp.';
      toast.classList.remove('toast--error');
      contactForm.reset();
      contactForm.querySelectorAll('.input-ok, .input-error').forEach(f => {
        f.classList.remove('input-ok', 'input-error');
      });
    } else {
      throw new Error();
    }
  } catch {
    toast.textContent = 'Hi ha hagut un error en enviar el missatge. Prova-ho de nou o contacta per WhatsApp.';
    toast.classList.add('toast--error');
  }

  toast.classList.add('show');
  submitBtn.textContent = originalText;
  submitBtn.disabled = false;
  setTimeout(() => toast.classList.remove('show'), 6000);
});
